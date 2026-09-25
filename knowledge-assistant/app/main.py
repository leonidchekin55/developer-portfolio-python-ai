import hashlib
import hmac
import json
import os
import re
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from redis.asyncio import Redis
from sqlalchemy import and_, inspect, or_, select, text, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import Session, engine, get_db
from app.models import Base, ChatMessage, Document, DocumentChunk, User
from app import rag
from app.rag import ask, index_document, _term_weights, effective_rag_mode

SESSION_COOKIE = "knowbase_session"
SESSION_TTL = 30 * 24 * 60 * 60
SESSION_SECRET = settings.session_secret or secrets.token_urlsafe(48)
MAX_DOCUMENTS_PER_USER = 10
_auth_attempts: dict[str, list[float]] = {}


def _migrate_user_columns(connection):
    inspector = inspect(connection)
    for table in ("documents", "chat_messages"):
        columns = {column["name"] for column in inspector.get_columns(table)}
        if "user_id" not in columns:
            connection.execute(text(f"ALTER TABLE {table} ADD COLUMN user_id INTEGER REFERENCES users(id)"))
        connection.execute(text(f"CREATE INDEX IF NOT EXISTS ix_{table}_user_id ON {table} (user_id)"))


@asynccontextmanager
async def lifespan(app):
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
        await connection.run_sync(_migrate_user_columns)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    if settings.rag_mode in {"extractive", "groq", "openrouter"}:
        async with Session() as db:
            sample_exists = await db.execute(select(Document.id).where(Document.filename == "demo-guide.txt").limit(1))
            if sample_exists.scalar_one_or_none() is None:
                sample = (
                    "Knowbase принимает PDF, DOCX и TXT. При загрузке документ разбивается на фрагменты, "
                    "а ответы содержат имя файла и номер страницы. В бесплатном демо поиск выполняется "
                    "локально по словам и показывает исходный фрагмент без внешней языковой модели. "
                    "Полная локальная версия использует Qdrant и Ollama для embeddings и генерации ответов."
                )
                document = Document(filename="demo-guide.txt", status="indexed", chunk_count=1)
                db.add(document)
                await db.flush()
                db.add(DocumentChunk(
                    document_id=document.id, page=1, chunk_index=0, text=sample,
                    terms_json=json.dumps(_term_weights(sample), ensure_ascii=False),
                ))
                await db.commit()
    yield


app = FastAPI(title="Knowledge Assistant", version="1.0.0", lifespan=lifespan)


def _session_token(user_id: int) -> str:
    expires = int(time.time()) + SESSION_TTL
    message = f"{user_id}.{expires}"
    signature = hmac.new(SESSION_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"{message}.{signature}"


def _decode_session(token: str | None) -> int | None:
    if not token:
        return None
    try:
        raw_user_id, raw_expiry, signature = token.split(".", 2)
        message = f"{raw_user_id}.{raw_expiry}"
        expected = hmac.new(SESSION_SECRET.encode(), message.encode(), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected) or int(raw_expiry) < int(time.time()):
            return None
        return int(raw_user_id)
    except (ValueError, TypeError):
        return None


def current_user_id(request: Request) -> int | None:
    return _decode_session(request.cookies.get(SESSION_COOKIE))


def _set_session_cookie(response: Response, request: Request, user_id: int) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        _session_token(user_id),
        max_age=SESSION_TTL,
        httponly=True,
        secure=request.url.scheme == "https" or request.url.hostname not in {"localhost", "127.0.0.1", "testserver"},
        samesite="strict",
        path="/",
    )


def _check_auth_rate_limit(request: Request) -> None:
    now = time.monotonic()
    address = request.client.host if request.client else "unknown"
    recent = [stamp for stamp in _auth_attempts.get(address, []) if now - stamp < 900]
    if len(recent) >= 12:
        raise HTTPException(429, "Слишком много попыток. Подождите 15 минут.")
    recent.append(now)
    _auth_attempts[address] = recent
    if len(_auth_attempts) > 10_000:
        _auth_attempts.clear()


def _hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${digest.hex()}"


def _verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt_hex, digest_hex = stored.split("$", 2)
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1, dklen=32)
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


class AccountInput(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=128)


class Question(BaseModel):
    question: str = Field(min_length=3, max_length=2000)


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/api/v1/mode")
def mode():
    return {"rag_mode": effective_rag_mode(), "max_upload_mb": settings.max_upload_mb, "uploads_require_account": True}


@app.get("/health/ready")
async def ready(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        if settings.redis_url:
            redis = Redis.from_url(settings.redis_url)
            await redis.ping()
            await redis.aclose()
        return {"status": "ready"}
    except Exception as error:
        raise HTTPException(503, "dependency unavailable") from error


@app.post("/api/v1/auth/register", status_code=201)
async def register(data: AccountInput, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    _check_auth_rate_limit(request)
    email = data.email.strip().lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise HTTPException(422, "Введите корректный email.")
    if await db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(409, "Аккаунт с таким email уже существует.")
    user = User(email=email, password_hash=_hash_password(data.password))
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as error:
        await db.rollback()
        raise HTTPException(409, "Аккаунт с таким email уже существует.") from error
    await db.refresh(user)
    _set_session_cookie(response, request, user.id)
    return {"id": user.id, "email": user.email}


@app.post("/api/v1/auth/login")
async def login(data: AccountInput, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    _check_auth_rate_limit(request)
    email = data.email.strip().lower()
    user = await db.scalar(select(User).where(User.email == email))
    if user is None or not _verify_password(data.password, user.password_hash):
        raise HTTPException(401, "Email или пароль неверны.")
    _set_session_cookie(response, request, user.id)
    return {"id": user.id, "email": user.email}


@app.post("/api/v1/auth/logout", status_code=204)
def logout(request: Request, response: Response):
    secure = request.url.scheme == "https" or request.url.hostname not in {"localhost", "127.0.0.1", "testserver"}
    response.delete_cookie(SESSION_COOKIE, path="/", httponly=True, secure=secure, samesite="strict")


@app.get("/api/v1/auth/me")
async def who_am_i(user_id: int | None = Depends(current_user_id), db: AsyncSession = Depends(get_db)):
    if user_id is None:
        return {"user": None}
    user = await db.get(User, user_id)
    return {"user": {"id": user.id, "email": user.email}} if user else {"user": None}


@app.post("/api/v1/documents")
async def upload(
    file: UploadFile = File(...),
    user_id: int | None = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if user_id is None:
        raise HTTPException(401, "Войдите или создайте аккаунт, чтобы загрузить документ.")
    count = await db.scalar(select(func.count()).select_from(Document).where(Document.user_id == user_id))
    if count >= MAX_DOCUMENTS_PER_USER:
        raise HTTPException(413, f"В одном аккаунте можно хранить не более {MAX_DOCUMENTS_PER_USER} документов.")
    extension = Path(file.filename or "").suffix.lower()
    if extension not in {".pdf", ".docx", ".txt"}:
        raise HTTPException(415, "Поддерживаются только PDF, DOCX и TXT.")
    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "Размер файла превышает допустимый лимит.")
    safe_name = Path(file.filename or "upload").name
    path = Path(settings.upload_dir) / f"{os.urandom(8).hex()}_{safe_name}"
    path.write_bytes(content)
    document = Document(filename=safe_name, status="indexing", user_id=user_id)
    db.add(document)
    await db.commit()
    await db.refresh(document)
    try:
        count = await index_document(document.id, safe_name, path, user_id=user_id)
        document.chunk_count = count
        document.status = "indexed" if count else "empty"
    except Exception as error:
        document.status = "failed"
        await db.commit()
        raise HTTPException(502, f"Не удалось обработать документ: {type(error).__name__}") from error
    finally:
        path.unlink(missing_ok=True)
    await db.commit()
    return {"id": document.id, "filename": document.filename, "status": document.status, "chunks": document.chunk_count}


def _visible_documents_query(user_id: int | None):
    query = select(Document)
    demo_sample = and_(Document.user_id.is_(None), Document.filename == "demo-guide.txt")
    if user_id is None:
        query = query.where(demo_sample)
    else:
        query = query.where(or_(Document.user_id == user_id, demo_sample))
    return query.order_by(Document.id.desc())


@app.get("/api/v1/documents")
async def documents(user_id: int | None = Depends(current_user_id), db: AsyncSession = Depends(get_db)):
    rows = await db.execute(_visible_documents_query(user_id))
    return [
        {"id": document.id, "filename": document.filename, "status": document.status,
         "chunks": document.chunk_count, "created_at": document.created_at.isoformat(),
         "deletable": user_id is not None and document.user_id == user_id}
        for document in rows.scalars()
    ]


@app.delete("/api/v1/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: int,
    user_id: int | None = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if user_id is None:
        raise HTTPException(401, "Войдите, чтобы удалить документ.")
    document = await db.scalar(select(Document).where(Document.id == document_id, Document.user_id == user_id))
    if document is None:
        raise HTTPException(404, "Документ не найден.")
    await db.execute(text("DELETE FROM document_chunks WHERE document_id = :document_id"), {"document_id": document.id})
    if rag.client is not None:
        try:
            if rag.client.collection_exists(rag.COLLECTION):
                rag.client.delete(
                    rag.COLLECTION,
                    points_selector=rag.models.FilterSelector(filter=rag.models.Filter(must=[
                        rag.models.FieldCondition(key="document_id", match=rag.models.MatchValue(value=document.id))
                    ])),
                )
        except Exception as error:
            raise HTTPException(503, "Не удалось удалить индекс документа. Повторите попытку.") from error
    history_rows = await db.execute(select(ChatMessage).where(ChatMessage.user_id == user_id))
    for message in history_rows.scalars():
        if any(source.get("filename") == document.filename for source in json.loads(message.sources_json or "[]")):
            await db.delete(message)
    await db.delete(document)
    await db.commit()


@app.post("/api/v1/chat")
async def chat(
    data: Question,
    user_id: int | None = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
):
    try:
        answer, sources = await ask(data.question, user_id=user_id)
    except httpx.HTTPStatusError as error:
        if error.response.status_code == 429:
            raise HTTPException(503, "Лимит AI-запросов временно исчерпан. Попробуйте позже.") from error
        raise HTTPException(502, "Внешний AI-сервис временно недоступен.") from error
    except Exception as error:
        raise HTTPException(502, f"Ошибка поиска: {type(error).__name__}") from error
    if user_id is not None:
        db.add(ChatMessage(user_id=user_id, question=data.question, answer=answer,
                           sources_json=json.dumps(sources, ensure_ascii=False)))
        await db.commit()
    return {"answer": answer, "sources": sources}


@app.get("/api/v1/history")
async def history(
    limit: int = 20,
    user_id: int | None = Depends(current_user_id),
    db: AsyncSession = Depends(get_db),
):
    if user_id is None:
        return []
    rows = await db.execute(
        select(ChatMessage).where(ChatMessage.user_id == user_id)
        .order_by(ChatMessage.id.desc()).limit(max(1, min(limit, 100)))
    )
    return [
        {"id": message.id, "question": message.question, "answer": message.answer,
         "sources": json.loads(message.sources_json), "created_at": message.created_at.isoformat()}
        for message in rows.scalars()
    ]


web_dist = Path(__file__).resolve().parent.parent / "web" / "dist"
if web_dist.exists():
    app.mount("/assets", StaticFiles(directory=web_dist / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    async def frontend():
        return FileResponse(web_dist / "index.html")
