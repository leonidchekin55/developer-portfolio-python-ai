import json,os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI,UploadFile,File,HTTPException,Depends
import httpx
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel,Field
from sqlalchemy import select,text
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.config import settings
from app.models import Base,Document,ChatMessage,DocumentChunk
from app.db import engine,Session,get_db
from app.rag import index_document,ask,_term_weights,effective_rag_mode
@asynccontextmanager
async def lifespan(app):
 async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
 Path(settings.upload_dir).mkdir(parents=True,exist_ok=True)
 if settings.rag_mode in {"extractive","groq","openrouter"}:
  async with Session() as db:
   if not (await db.execute(select(Document).where(Document.filename=="demo-guide.txt").limit(1))).scalar_one_or_none():
    filename="demo-guide.txt"
    sample="Knowbase принимает PDF, DOCX и TXT. При загрузке документ разбивается на фрагменты, а ответы содержат имя файла и номер страницы. В бесплатном демо поиск выполняется локально по словам и показывает исходный фрагмент без внешней языковой модели. Полная локальная версия использует Qdrant и Ollama для embeddings и генерации ответов."
    doc=Document(filename=filename,status="indexed",chunk_count=1); db.add(doc); await db.flush()
    db.add(DocumentChunk(document_id=doc.id,page=1,chunk_index=0,text=sample,terms_json=json.dumps(_term_weights(sample),ensure_ascii=False)))
    await db.commit()
 yield
app=FastAPI(title="Knowledge Assistant",version="1.0.0",lifespan=lifespan)
@app.get("/health/live")
def live(): return {"status":"ok"}
@app.get("/api/v1/mode")
def mode(): return {"rag_mode":effective_rag_mode(),"max_upload_mb":settings.max_upload_mb,"uploads_enabled":settings.allow_public_uploads,"history_enabled":settings.allow_public_uploads}
@app.get("/health/ready")
async def ready(db:AsyncSession=Depends(get_db)):
 try:
  await db.execute(text("SELECT 1"))
  if settings.redis_url:
   r=Redis.from_url(settings.redis_url); await r.ping(); await r.aclose()
  return {"status":"ready"}
 except Exception as e: raise HTTPException(503,"dependency unavailable") from e
@app.post("/api/v1/documents")
async def upload(file:UploadFile=File(...),db:AsyncSession=Depends(get_db)):
 if not settings.allow_public_uploads: raise HTTPException(403,"Загрузка отключена в общей демоверсии. Используется только встроенный демонстрационный документ.")
 ext=Path(file.filename or "").suffix.lower()
 if ext not in {".pdf",".docx",".txt"}: raise HTTPException(415,"Supported formats: PDF, DOCX, TXT")
 content=await file.read(settings.max_upload_mb*1024*1024+1)
 if len(content)>settings.max_upload_mb*1024*1024: raise HTTPException(413,"File exceeds upload limit")
 safe_name=Path(file.filename or "upload").name; path=Path(settings.upload_dir)/f"{os.urandom(8).hex()}_{safe_name}"; path.write_bytes(content)
 doc=Document(filename=safe_name,status="indexing"); db.add(doc); await db.commit(); await db.refresh(doc)
 try:
  count=await index_document(doc.id,safe_name,path); doc.chunk_count=count; doc.status="indexed" if count else "empty"
 except Exception as e:
  doc.status="failed"; await db.commit(); raise HTTPException(502,f"Indexing failed: {type(e).__name__}") from e
 finally:
  path.unlink(missing_ok=True)
 await db.commit(); return {"id":doc.id,"filename":doc.filename,"status":doc.status,"chunks":doc.chunk_count}
@app.get("/api/v1/documents")
async def documents(db:AsyncSession=Depends(get_db)):
 query=select(Document).order_by(Document.id.desc())
 if not settings.allow_public_uploads: query=query.where(Document.filename=="demo-guide.txt")
 rows=await db.execute(query); return [{"id":d.id,"filename":d.filename,"status":d.status,"chunks":d.chunk_count,"created_at":d.created_at.isoformat()} for d in rows.scalars()]
class Question(BaseModel): question:str=Field(min_length=3,max_length=2000)
@app.post("/api/v1/chat")
async def chat(data:Question,db:AsyncSession=Depends(get_db)):
 try: answer,sources=await ask(data.question)
 except httpx.HTTPStatusError as e:
  if e.response.status_code==429: raise HTTPException(503,"Лимит AI-запросов временно исчерпан. Попробуйте позже.") from e
  raise HTTPException(502,"Внешний AI-сервис временно недоступен.") from e
 except Exception as e: raise HTTPException(502,f"RAG request failed: {type(e).__name__}") from e
 if settings.allow_public_uploads:
  db.add(ChatMessage(question=data.question,answer=answer,sources_json=json.dumps(sources,ensure_ascii=False))); await db.commit()
 return {"answer":answer,"sources":sources}
@app.get("/api/v1/history")
async def history(limit:int=20,db:AsyncSession=Depends(get_db)):
 if not settings.allow_public_uploads: return []
 rows=await db.execute(select(ChatMessage).order_by(ChatMessage.id.desc()).limit(max(1,min(limit,100))))
 return [{"id":m.id,"question":m.question,"answer":m.answer,"sources":json.loads(m.sources_json),"created_at":m.created_at.isoformat()} for m in rows.scalars()]

web_dist=Path(__file__).resolve().parent.parent/"web"/"dist"
if web_dist.exists():
 app.mount("/assets",StaticFiles(directory=web_dist/"assets"),name="assets")
 @app.get("/",include_in_schema=False)
 async def frontend(): return FileResponse(web_dist/"index.html")
