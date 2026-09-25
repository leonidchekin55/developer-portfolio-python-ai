import base64
import hashlib
import hmac
import json
import secrets
import time
from contextlib import asynccontextmanager
from threading import Lock
from uuid import uuid4

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from redis.asyncio import Redis
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import create_token, hash_password, token_user, verify_password
from app.db import Session, engine, get_db
from app.events import publish, subscribe, unsubscribe
from app.metrics import LATENCY, REQUESTS, metrics_response
from app.models.entities import Base, Project, Task, User, WebhookEvent
from app.schemas import DemoProjectIn, DemoTaskIn, DemoTaskStatusIn, ProjectIn, TaskIn, WebhookIn
from app.worker import task_created_notification

oauth=OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")
@asynccontextmanager
async def lifespan(app):
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    async with Session() as db:
        user=(await db.execute(select(User).where(User.email=="demo@pulseboard.local"))).scalar_one_or_none()
        if not user:
            demo_password = settings.demo_password
            if not demo_password and settings.app_env != "production":
                demo_password = "ChangeMe123!"
            if demo_password:
                user=User(email="demo@pulseboard.local",password_hash=hash_password(demo_password),tenant_id="demo",role="owner")
                db.add(user)
                await db.flush()
        project=(await db.execute(select(Project).where(Project.tenant_id=="demo",Project.name=="Portfolio Demo"))).scalar_one_or_none()
        if not project and user:
            project=Project(tenant_id="demo",name="Portfolio Demo",description="Sample SaaS project for exploring the API.")
            db.add(project); await db.flush()
            db.add(Task(tenant_id="demo",project_id=project.id,title="Explore the API endpoints",created_by=user.id))
        await db.commit()
    yield
app=FastAPI(title="Pulseboard API",version="1.0.0",description="Multi-tenant task SaaS demo",lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["https://leonid-portfolio.onrender.com", "http://localhost:8765", "http://127.0.0.1:8765"], allow_methods=["GET", "POST", "PATCH", "OPTIONS"], allow_headers=["Authorization", "Content-Type"], max_age=600)
@app.middleware("http")
async def instrument(request,call_next):
    start=time.perf_counter(); response=await call_next(request); LATENCY.observe(time.perf_counter()-start); REQUESTS.labels(request.method,request.url.path,str(response.status_code)).inc(); return response
@app.get("/metrics",include_in_schema=False)
def metrics():
    body,media=metrics_response(); return Response(body,media_type=media)
@app.get("/health/live")
def live(): return {"status":"ok"}
@app.get("/health/ready")
async def ready(db:AsyncSession=Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        if settings.redis_url:
            r=Redis.from_url(settings.redis_url); await r.ping(); await r.aclose()
        return {"status":"ready"}
    except Exception as exc: raise HTTPException(503,"dependency unavailable") from exc
async def current_user(token:str=Depends(oauth),db:AsyncSession=Depends(get_db)):
    try: uid=token_user(token)
    except ValueError as e: raise HTTPException(401,"Invalid credentials") from e
    user=await db.get(User,uid)
    if not user or not user.active: raise HTTPException(401,"Inactive or missing user")
    return user
async def owner(user:User=Depends(current_user)):
    if user.role!="owner": raise HTTPException(403,"Owner role required")
    return user

# Public portfolio board sessions use a separate, short-lived in-memory store.
# They never receive a database user/JWT and cannot access the SaaS endpoints.
_demo_sessions: dict[str, dict] = {}
_demo_lock = Lock()
_demo_ip_windows: dict[str, list[float]] = {}
_DEMO_TTL = 2 * 60 * 60
_DEMO_MAX_PROJECTS = 12
_DEMO_MAX_TASKS = 80

def _demo_token(session_id: str, expires_at: int) -> str:
    payload = json.dumps({"sid": session_id, "exp": expires_at, "scope": "pulseboard-demo"}, separators=(",", ":")).encode()
    encoded = base64.urlsafe_b64encode(payload).rstrip(b"=").decode()
    signature = hmac.new(settings.secret_key.encode(), encoded.encode(), hashlib.sha256).digest()
    return f"{encoded}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"

def _demo_session_id(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Demo session required")
    try:
        encoded, signature = authorization[7:].split(".", 1)
        expected = base64.urlsafe_b64encode(hmac.new(settings.secret_key.encode(), encoded.encode(), hashlib.sha256).digest()).rstrip(b"=").decode()
        if not hmac.compare_digest(signature, expected): raise ValueError
        raw = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
        claims = json.loads(raw)
        if claims.get("scope") != "pulseboard-demo" or int(claims["exp"]) <= int(time.time()): raise ValueError
        session_id = str(claims["sid"])
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(401, "Demo session expired")
    with _demo_lock:
        session = _demo_sessions.get(session_id)
        if not session or session["expires_at"] <= time.time():
            _demo_sessions.pop(session_id, None)
            raise HTTPException(410, "Demo session is no longer available")
    return session_id

def _demo_snapshot(session_id: str) -> dict:
    session = _demo_sessions[session_id]
    return {"projects": session["projects"], "tasks": session["tasks"]}

@app.post("/api/v1/demo/session")
def create_demo_session(request: Request):
    now = time.time()
    forwarded = request.headers.get("x-forwarded-for", "")
    ip = forwarded.split(",", 1)[0].strip() or (request.client.host if request.client else "unknown")
    with _demo_lock:
        for expired in [key for key, value in _demo_sessions.items() if value["expires_at"] <= now]:
            _demo_sessions.pop(expired, None)
        recent = [stamp for stamp in _demo_ip_windows.get(ip, []) if now - stamp < 3600]
        if len(recent) >= 12: raise HTTPException(429, "Too many demo sessions; try again later")
        recent.append(now); _demo_ip_windows[ip] = recent
        session_id = secrets.token_urlsafe(24)
        expires_at = int(now + _DEMO_TTL)
        project_id = str(uuid4()); assistant_id = str(uuid4())
        _demo_sessions[session_id] = {"expires_at": expires_at,
            "projects": [{"id": project_id, "name": "Портфолио"}, {"id": assistant_id, "name": "AI-помощник"}],
            "tasks": [
                {"id": str(uuid4()), "project_id": project_id, "title": "Собрать обратную связь по макету", "status": "todo"},
                {"id": str(uuid4()), "project_id": project_id, "title": "Подготовить список страниц для запуска", "status": "doing"},
                {"id": str(uuid4()), "project_id": assistant_id, "title": "Проверить ответы по документам", "status": "todo"},
                {"id": str(uuid4()), "project_id": assistant_id, "title": "Добавить источники к ответам", "status": "done"},
            ]}
    return {"access_token": _demo_token(session_id, expires_at), "token_type": "bearer", "expires_in": _DEMO_TTL}

@app.get("/api/v1/demo/board")
def demo_board(authorization: str | None = Header(default=None)):
    sid = _demo_session_id(authorization)
    with _demo_lock: return _demo_snapshot(sid)

@app.post("/api/v1/demo/projects", status_code=201)
def demo_create_project(data: DemoProjectIn, authorization: str | None = Header(default=None)):
    sid = _demo_session_id(authorization)
    with _demo_lock:
        session = _demo_sessions[sid]
        if len(session["projects"]) >= _DEMO_MAX_PROJECTS: raise HTTPException(429, "Demo project limit reached")
        item = {"id": str(uuid4()), "name": data.name}
        session["projects"].append(item)
        return item

@app.post("/api/v1/demo/tasks", status_code=201)
def demo_create_task(data: DemoTaskIn, authorization: str | None = Header(default=None)):
    sid = _demo_session_id(authorization)
    with _demo_lock:
        session = _demo_sessions[sid]
        if len(session["tasks"]) >= _DEMO_MAX_TASKS: raise HTTPException(429, "Demo task limit reached")
        if not any(project["id"] == data.project_id for project in session["projects"]): raise HTTPException(404, "Project not found")
        item = {"id": str(uuid4()), "project_id": data.project_id, "title": data.title, "status": "todo"}
        session["tasks"].insert(0, item)
        return item

@app.patch("/api/v1/demo/tasks/{task_id}")
def demo_update_task(task_id: str, data: DemoTaskStatusIn, authorization: str | None = Header(default=None)):
    sid = _demo_session_id(authorization)
    with _demo_lock:
        session = _demo_sessions[sid]
        task = next((item for item in session["tasks"] if item["id"] == task_id), None)
        if not task: raise HTTPException(404, "Task not found")
        task["status"] = data.status
        return task

@app.post("/api/v1/demo/reset")
def demo_reset(authorization: str | None = Header(default=None)):
    sid = _demo_session_id(authorization)
    with _demo_lock:
        project_id = str(uuid4()); assistant_id = str(uuid4())
        _demo_sessions[sid]["projects"] = [{"id": project_id, "name": "Портфолио"}, {"id": assistant_id, "name": "AI-помощник"}]
        _demo_sessions[sid]["tasks"] = [
            {"id": str(uuid4()), "project_id": project_id, "title": "Собрать обратную связь по макету", "status": "todo"},
            {"id": str(uuid4()), "project_id": project_id, "title": "Подготовить список страниц для запуска", "status": "doing"},
            {"id": str(uuid4()), "project_id": assistant_id, "title": "Проверить ответы по документам", "status": "todo"},
            {"id": str(uuid4()), "project_id": assistant_id, "title": "Добавить источники к ответам", "status": "done"},
        ]
    return {"ok": True}
@app.post("/api/v1/auth/token")
async def login(form:OAuth2PasswordRequestForm=Depends(),db:AsyncSession=Depends(get_db)):
    user=(await db.execute(select(User).where(User.email==form.username))).scalar_one_or_none()
    if not user or not user.active or not verify_password(form.password,user.password_hash): raise HTTPException(401,"Incorrect email or password")
    return {"access_token":create_token(user.id),"token_type":"bearer","role":user.role}
@app.get("/api/v1/me")
def me(user:User=Depends(current_user)): return {"id":user.id,"email":user.email,"tenant_id":user.tenant_id,"role":user.role}
@app.get("/api/v1/projects")
async def projects(user:User=Depends(current_user),db:AsyncSession=Depends(get_db)):
    rows=await db.execute(select(Project).where(Project.tenant_id==user.tenant_id)); return [{"id":p.id,"name":p.name,"description":p.description} for p in rows.scalars()]
@app.post("/api/v1/projects",status_code=201)
async def create_project(data:ProjectIn,user:User=Depends(owner),db:AsyncSession=Depends(get_db)):
    item=Project(tenant_id=user.tenant_id,name=data.name,description=data.description); db.add(item); await db.commit(); await db.refresh(item); return {"id":item.id,"name":item.name,"description":item.description}
@app.get("/api/v1/tasks")
async def tasks(user:User=Depends(current_user),db:AsyncSession=Depends(get_db)):
    rows=await db.execute(select(Task).where(Task.tenant_id==user.tenant_id)); return [{"id":t.id,"project_id":t.project_id,"title":t.title,"status":t.status} for t in rows.scalars()]
@app.post("/api/v1/tasks",status_code=201)
async def create_task(data:TaskIn,user:User=Depends(current_user),db:AsyncSession=Depends(get_db)):
    project=(await db.execute(select(Project).where(Project.id==data.project_id,Project.tenant_id==user.tenant_id))).scalar_one_or_none()
    if not project: raise HTTPException(404,"Project not found")
    item=Task(tenant_id=user.tenant_id,project_id=data.project_id,title=data.title,created_by=user.id); db.add(item); await db.commit(); await db.refresh(item)
    if settings.celery_eager: task_created_notification.run(item.id)
    else: task_created_notification.delay(item.id)
    await publish(user.tenant_id,{"type":"task.created","task_id":item.id,"title":item.title}); return {"id":item.id,"title":item.title,"status":item.status}
@app.post("/api/v1/webhooks/demo")
async def webhook(data:WebhookIn,x_signature:str=Header(),idempotency_key:str=Header(alias="Idempotency-Key"),user:User=Depends(owner),db:AsyncSession=Depends(get_db)):
    raw=json.dumps(data.model_dump(),separators=(",",":"),sort_keys=True).encode(); expected=hmac.new(settings.webhook_secret.encode(),raw,hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected,x_signature): raise HTTPException(401,"Invalid signature")
    existing=(await db.execute(select(WebhookEvent).where(WebhookEvent.tenant_id==user.tenant_id,WebhookEvent.idempotency_key==idempotency_key))).scalar_one_or_none()
    if existing: return {"accepted":True,"duplicate":True}
    db.add(WebhookEvent(tenant_id=user.tenant_id,idempotency_key=idempotency_key,payload=raw.decode(),processed=True)); await db.commit(); await publish(user.tenant_id,{"type":"webhook.received","event":data.event}); return {"accepted":True,"duplicate":False}
@app.websocket("/api/v1/events")
async def event_socket(ws:WebSocket,token:str):
    try: uid=token_user(token)
    except ValueError: await ws.close(code=4401); return
    async with Session() as db: user=await db.get(User,uid)
    if not user: await ws.close(code=4401); return
    await ws.accept()
    if not settings.redis_url:
        queue=subscribe(user.tenant_id)
        try:
            await ws.send_json({"type":"connected","tenant_id":user.tenant_id})
            while True: await ws.send_text(await queue.get())
        except WebSocketDisconnect: pass
        finally: unsubscribe(user.tenant_id,queue)
        return
    r=Redis.from_url(settings.redis_url,decode_responses=True); pubsub=r.pubsub(); await pubsub.subscribe(f"tenant:{user.tenant_id}:events")
    try:
        await ws.send_json({"type":"connected","tenant_id":user.tenant_id})
        async for message in pubsub.listen():
            if message["type"]=="message": await ws.send_text(message["data"])
    except WebSocketDisconnect: pass
    finally: await pubsub.aclose(); await r.aclose()
