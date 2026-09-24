import hashlib
import hmac
import json
import time
from contextlib import asynccontextmanager

from fastapi import (
    Depends,
    FastAPI,
    Header,
    HTTPException,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
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
from app.schemas import ProjectIn, TaskIn, WebhookIn
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
