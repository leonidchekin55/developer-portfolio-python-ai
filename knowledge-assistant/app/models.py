from datetime import datetime,timezone
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column
from sqlalchemy import String,Text,DateTime,Integer
class Base(DeclarativeBase): pass
class Document(Base):
 __tablename__="documents"
 id:Mapped[int]=mapped_column(primary_key=True)
 filename:Mapped[str]=mapped_column(String(255))
 status:Mapped[str]=mapped_column(String(30),default="indexed")
 chunk_count:Mapped[int]=mapped_column(Integer,default=0)
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class ChatMessage(Base):
 __tablename__="chat_messages"
 id:Mapped[int]=mapped_column(primary_key=True)
 question:Mapped[str]=mapped_column(Text)
 answer:Mapped[str]=mapped_column(Text)
 sources_json:Mapped[str]=mapped_column(Text,default="[]")
 created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
