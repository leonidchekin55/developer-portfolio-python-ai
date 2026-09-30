import re
from collections import Counter
from math import log1p
from pathlib import Path
from fastapi import Depends, UploadFile, File, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from shared.core import create_app,get_db,Document,DocumentChunk,user_from_token,engine,settings
from shared.embeddings import embed_texts,cosine_similarity
app=create_app("02 · AI Knowledge Base","Multi-user knowledge base with chunking, lexical retrieval and source citations")
MAX_TEXT_CHARS=200_000

def tokenize(text:str)->set[str]:
    return {t for t in re.findall(r"[\w@.+-]+",text.casefold(),flags=re.UNICODE) if len(t)>1}
def split_chunks(text:str,size:int=700,overlap:int=100):
    if not 0 <= overlap < size: raise ValueError("overlap must be smaller than size")
    text=" ".join(text.split()); chunks=[]; start=0
    while start<len(text):
        end=min(len(text),start+size); chunks.append(text[start:end])
        if end==len(text): break
        start=end-overlap
    return chunks
class DocumentInput(BaseModel):
    text:str=Field(min_length=1,max_length=MAX_TEXT_CHARS)
    filename:str=Field(default="inline.txt",min_length=1,max_length=200)
class Query(BaseModel): question:str=Field(min_length=2,max_length=2000); top_k:int=Field(default=3,ge=1,le=10)
def persist(text:str,filename:str,db:Session,owner:str):
    chunks=split_chunks(text)
    vectors=embed_texts(chunks)
    d=Document(owner=owner,filename=Path(filename).name,text=text,status="indexed",chunks=chunks); db.add(d); db.flush()
    db.add_all([DocumentChunk(document_id=d.id,owner=owner,ordinal=i,content=chunk,embedding=vector) for i,(chunk,vector) in enumerate(zip(chunks,vectors))])
    db.commit(); db.refresh(d)
    return {"id":d.id,"filename":d.filename,"chunks":len(d.chunks),"embedding_mode":settings.embedding_mode,"status":d.status}
@app.post("/documents")
def add(body:DocumentInput,db:Session=Depends(get_db),owner:str=Depends(user_from_token)):
    return persist(body.text,body.filename,db,owner)
@app.post("/documents/upload")
async def upload(file:UploadFile=File(...),db:Session=Depends(get_db),owner:str=Depends(user_from_token)):
    filename=Path(file.filename or "").name
    if Path(filename).suffix.lower() not in {".txt",".md"}: raise HTTPException(415,"This upload endpoint accepts .txt and .md; use Document Processor for PDF/DOCX")
    data=await file.read(MAX_TEXT_CHARS+1)
    if len(data)>MAX_TEXT_CHARS: raise HTTPException(413,"Document exceeds 200 KB text limit")
    return persist(data.decode("utf-8",errors="replace"),filename,db,owner)
@app.get("/documents")
def documents(db:Session=Depends(get_db),owner:str=Depends(user_from_token)):
    return [{"id":d.id,"filename":d.filename,"status":d.status,"created_at":d.created_at} for d in db.query(Document).filter(Document.owner==owner).order_by(Document.created_at.desc()).limit(100)]
def retrieve_documents(db:Session,owner:str,question:str,top_k:int=3)->dict:
    terms=tokenize(question)
    if not terms: return {"answer":"Вопрос не содержит поисковых слов.","citations":[],"retrieval":"hybrid-vector-search","results":[]}
    query_vector=embed_texts([question])[0]
    if engine.dialect.name=="postgresql":
        distance=DocumentChunk.embedding.cosine_distance(query_vector)
        rows=db.query(DocumentChunk,distance.label("distance")).filter(DocumentChunk.owner==owner).order_by(distance).limit(200).all()
        candidate_chunks=[(row[0],1-float(row[1])) for row in rows]
        # Old SQLite/early demo records may have only the JSON chunks column. Include those until reindexed.
        docs=db.query(Document).filter(Document.owner==owner,Document.status=="indexed",~Document.id.in_(db.query(DocumentChunk.document_id).filter(DocumentChunk.owner==owner))).all()
    else:
        chunks=db.query(DocumentChunk).filter(DocumentChunk.owner==owner).all()
        candidate_chunks=[(chunk,cosine_similarity(query_vector,chunk.embedding)) for chunk in chunks]
        docs=db.query(Document).filter(Document.owner==owner,Document.status=="indexed").all()
    hits=[]
    doc_ids={chunk.document_id for chunk,_ in candidate_chunks}
    names={d.id:d.filename for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()} if doc_ids else {}
    for chunk,similarity in candidate_chunks:
        tokens=re.findall(r"[\w@.+-]+",chunk.content.casefold(),flags=re.UNICODE); counts=Counter(tokens); matched=terms & set(counts)
        lexical=len(matched)/len(terms)
        if lexical==0 and similarity<0.55: continue
        combined=round(0.65*max(0.0,min(1.0,similarity))+0.35*lexical,4)
        hits.append({"score":combined,"vector_similarity":round(similarity,4),"document_id":chunk.document_id,"filename":names.get(chunk.document_id,"document"),"chunk":chunk.ordinal,"text":chunk.content,"citation":f"{names.get(chunk.document_id,'document')} · фрагмент {chunk.ordinal+1}"})
    chunk_doc_ids={chunk.document_id for chunk,_ in candidate_chunks}
    for doc in docs:
        if doc.id in chunk_doc_ids: continue
        legacy_vectors=embed_texts(doc.chunks)
        for ordinal,(content,vector) in enumerate(zip(doc.chunks,legacy_vectors)):
            similarity=cosine_similarity(query_vector,vector); tokens=re.findall(r"[\w@.+-]+",content.casefold(),flags=re.UNICODE); lexical=len(terms & set(tokens))/len(terms)
            if lexical==0 and similarity<0.55: continue
            hits.append({"score":round(0.65*max(0.0,min(1.0,similarity))+0.35*lexical,4),"vector_similarity":round(similarity,4),"document_id":doc.id,"filename":doc.filename,"chunk":ordinal,"text":content,"citation":f"{doc.filename} · фрагмент {ordinal+1}"})
    hits.sort(key=lambda x:(-x["score"],x["filename"],x["chunk"])); hits=hits[:top_k]
    answer="\n\n".join(h["text"] for h in hits) if hits else "В доступных документах ответа не найдено."
    backend="pgvector HNSW" if engine.dialect.name=="postgresql" else "local cosine vectors"
    return {"answer":answer,"citations":[h["citation"] for h in hits],"retrieval":f"hybrid {backend} + lexical; embeddings={settings.embedding_mode}","results":hits}
@app.post("/search")
def search(body:Query,db:Session=Depends(get_db),owner:str=Depends(user_from_token)):
    return retrieve_documents(db,owner,body.question,body.top_k)
