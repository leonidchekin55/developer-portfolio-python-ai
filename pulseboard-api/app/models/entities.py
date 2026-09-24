from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase): pass
class User(Base):
    __tablename__="users"
    id:Mapped[int]=mapped_column(primary_key=True)
    email:Mapped[str]=mapped_column(String(255), unique=True, index=True)
    password_hash:Mapped[str]=mapped_column(String(255))
    tenant_id:Mapped[str]=mapped_column(String(64), index=True)
    role:Mapped[str]=mapped_column(String(20), default="member")
    active:Mapped[bool]=mapped_column(Boolean, default=True)
class Project(Base):
    __tablename__="projects"
    id:Mapped[int]=mapped_column(primary_key=True)
    tenant_id:Mapped[str]=mapped_column(String(64), index=True)
    name:Mapped[str]=mapped_column(String(180))
    description:Mapped[str]=mapped_column(Text, default="")
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True), default=lambda:datetime.now(UTC))
class Task(Base):
    __tablename__="tasks"
    id:Mapped[int]=mapped_column(primary_key=True)
    tenant_id:Mapped[str]=mapped_column(String(64), index=True)
    project_id:Mapped[int]=mapped_column(ForeignKey("projects.id"))
    title:Mapped[str]=mapped_column(String(240))
    status:Mapped[str]=mapped_column(String(20), default="todo")
    created_by:Mapped[int]=mapped_column(ForeignKey("users.id"))
class WebhookEvent(Base):
    __tablename__="webhook_events"
    __table_args__=(UniqueConstraint("tenant_id","idempotency_key",name="uq_webhook_idempotency"),)
    id:Mapped[int]=mapped_column(primary_key=True)
    tenant_id:Mapped[str]=mapped_column(String(64), index=True)
    idempotency_key:Mapped[str]=mapped_column(String(160))
    payload:Mapped[str]=mapped_column(Text)
    processed:Mapped[bool]=mapped_column(Boolean, default=False)
