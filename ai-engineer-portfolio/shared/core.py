from __future__ import annotations
import time, uuid, hmac
from datetime import datetime, timezone
from typing import Generator
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import Response
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from sqlalchemy import create_engine, String, Text, DateTime, JSON, Integer, Float, inspect, text, update
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, Session
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from pgvector.sqlalchemy import Vector

class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite:///./portfolio.db"
    llm_mode: str = "mock"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    api_token: str = "demo-token-change-me"
    reader_api_token: str = "reader-token"
    upload_dir: str = "./data/uploads"
    redis_url: str = "redis://localhost:6379/0"
    celery_enabled: bool = False
    embedding_mode: str = "hash"
    embedding_model: str = "text-embedding-3-small"
    fastembed_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @model_validator(mode="after")
    def validate_settings(self):
        if self.embedding_mode not in {"hash", "openai", "fastembed"}:
            raise ValueError("EMBEDDING_MODE must be hash, openai or fastembed")
        if self.llm_mode not in {"mock", "openai"}:
            raise ValueError("LLM_MODE must be mock or openai")
        if self.api_token == self.reader_api_token:
            raise ValueError("Admin and reader tokens must be different")
        if self.app_env.lower() in {"production", "prod"} and (self.api_token == "demo-token-change-me" or self.reader_api_token == "reader-token" or len(self.api_token)<32 or len(self.reader_api_token)<32):
            raise ValueError("Set distinct tokens of at least 32 characters before production")
        return self
settings = Settings()
engine = create_engine(settings.database_url, connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
class Base(DeclarativeBase): pass
class Lead(Base):
    __tablename__ = "leads"
    owner: Mapped[str] = mapped_column(String, index=True, default="demo-admin")
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda:str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, default="")
    contact: Mapped[str] = mapped_column(String, default="")
    request: Mapped[str] = mapped_column(Text, default="")
    budget: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="new")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda:datetime.now(timezone.utc))
class Document(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda:str(uuid.uuid4()))
    owner: Mapped[str] = mapped_column(String, index=True, default="demo")
    filename: Mapped[str] = mapped_column(String)
    text: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="queued")
    processing_error: Mapped[str | None] = mapped_column(String, nullable=True, default=None)
    chunks: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda:datetime.now(timezone.utc))
class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda:str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String, index=True)
    owner: Mapped[str] = mapped_column(String, index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    embedding_mode: Mapped[str] = mapped_column(String, default="hash", server_default="hash")
    embedding: Mapped[list] = mapped_column(Vector(384).with_variant(JSON(), "sqlite"))
class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda:str(uuid.uuid4()))
    actor: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda:datetime.now(timezone.utc))
class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda:str(uuid.uuid4()))
    actor: Mapped[str] = mapped_column(String)
    action: Mapped[str] = mapped_column(String)
    detail: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda:datetime.now(timezone.utc))
class EvalRun(Base):
    __tablename__ = "eval_runs"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda:str(uuid.uuid4()))
    dataset: Mapped[str] = mapped_column(String)
    model: Mapped[str] = mapped_column(String)
    prompt_version: Mapped[str] = mapped_column(String)
    quality: Mapped[float] = mapped_column(Float)
    cost_usd: Mapped[float] = mapped_column(Float)
    latency_ms: Mapped[int] = mapped_column(Integer)
    trace: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda:datetime.now(timezone.utc))
def get_db() -> Generator[Session,None,None]:
    db=SessionLocal()
    try: yield db
    finally: db.close()
def init_db():
    if engine.dialect.name=="postgresql":
        with engine.begin() as connection: connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(engine)
    if engine.dialect.name=="postgresql":
        with engine.begin() as connection:
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_document_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops)"))
    # Small idempotent forward migration for databases made by portfolio v0.1.
    if "leads" in inspect(engine).get_table_names():
        columns={column["name"] for column in inspect(engine).get_columns("leads")}
        if "owner" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE leads ADD COLUMN owner VARCHAR NOT NULL DEFAULT 'demo-admin'"))
        with engine.begin() as connection:
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_leads_owner ON leads (owner)"))
    if "documents" in inspect(engine).get_table_names():
        columns={column["name"] for column in inspect(engine).get_columns("documents")}
        if "processing_error" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE documents ADD COLUMN processing_error VARCHAR"))
    if "document_chunks" in inspect(engine).get_table_names():
        columns={column["name"] for column in inspect(engine).get_columns("document_chunks")}
        if "embedding_mode" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE document_chunks ADD COLUMN embedding_mode VARCHAR NOT NULL DEFAULT 'hash'"))
def user_from_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401,"Bearer token required")
    token=authorization.split(" ",1)[1].strip()
    if hmac.compare_digest(token, settings.api_token): return "demo-admin"
    if hmac.compare_digest(token, settings.reader_api_token): return "demo-reader"
    raise HTTPException(403,"Invalid token")

REQUEST_COUNT = Counter("portfolio_http_requests_total", "HTTP requests", ["method", "status"])
REQUEST_LATENCY = Histogram("portfolio_http_request_duration_seconds", "HTTP request duration")
def create_app(title: str, description: str) -> FastAPI:
    from contextlib import asynccontextmanager
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        init_db()
        yield
    app=FastAPI(title=title, description=description, version="0.1.0", lifespan=lifespan)
    @app.middleware("http")
    async def timing(request: Request, call_next):
        start=time.perf_counter(); response=await call_next(request)
        elapsed=time.perf_counter()-start
        REQUEST_COUNT.labels(request.method,str(response.status_code)).inc()
        REQUEST_LATENCY.observe(elapsed)
        response.headers["X-Process-Time-Ms"]=str(round(elapsed*1000,2))
        return response
    @app.get("/health", tags=["system"])
    def health(): return {"status":"ok","llm_mode":settings.llm_mode}
    @app.get("/metrics", include_in_schema=False)
    def metrics(): return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
    return app
def record_audit(db:Session, actor:str, action:str, detail:dict):
    db.add(AuditEvent(actor=actor,action=action,detail=detail)); db.commit()
