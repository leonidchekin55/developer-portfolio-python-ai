import re
from fastapi import Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy.orm import Session
from shared.core import create_app,get_db,Approval,Lead,AuditEvent,record_audit,user_from_token
from shared.llm import choose_secure_tool
app=create_app("06 · Secure AI Agent","Role-gated CRM demo with fixed tools, validated proposals, approvals and audit events")
class AgentRequest(BaseModel): message:str=Field(min_length=1,max_length=3000)
class NoteArguments(BaseModel): note:str=Field(min_length=1,max_length=500)
class ApprovalDecision(BaseModel): approved:bool
ROLES={"demo-admin":{"crm.read","crm.write","approval.decide","audit.read"},"demo-reader":{"crm.read"}}
INJECTION_PATTERNS=(r"ignore\s+(all\s+)?(previous|prior|system)\s+instructions",r"reveal\s+(the\s+)?system\s+prompt",r"send\s+(the\s+)?password",r"ignore\s+all\s+rules",r"игнорируй\s+(все\s+)?(предыдущие|системные)\s+инструкции",r"раскрой\s+(системный\s+)?промпт",r"покажи\s+системный\s+промпт",r"отправь\s+пароль")
def blocked_input(text:str)->bool:
    normalized=" ".join(text.casefold().split())
    return any(re.search(pattern,normalized) for pattern in INJECTION_PATTERNS)
def require(actor:str,permission:str):
    if permission not in ROLES.get(actor,set()): raise HTTPException(403,"Role lacks required permission")
@app.post("/agent")
def agent(body:AgentRequest,db:Session=Depends(get_db),actor:str=Depends(user_from_token)):
    if blocked_input(body.message):
        record_audit(db,actor,"blocked_prompt_injection",{"message_preview":body.message[:80]})
        return {"response":"Запрос заблокирован демонстрационной политикой безопасности.","actions":[],"blocked":True}
    allowed=[tool for tool,permission in (("crm.read","crm.read"),("crm.create_note","crm.write")) if permission in ROLES[actor]]
    try: selected=choose_secure_tool(body.message,allowed)
    except Exception as exc: raise HTTPException(502,"Tool selection failed") from exc
    if selected is None:
        record_audit(db,actor,"agent.answer",{"message_length":len(body.message)})
        return {"response":"Демо поддерживает чтение CRM-заявок и подготовку заметки на запись с подтверждением.","actions":[]}
    tool=selected.get("tool")
    if tool not in allowed: raise HTTPException(403,"Selected tool is not allowed for this role")
    if tool=="crm.read":
        require(actor,"crm.read")
        if selected.get("arguments")!={}: raise HTTPException(422,"Invalid read tool arguments")
        leads=db.query(Lead).filter(Lead.owner==actor).order_by(Lead.created_at.desc()).limit(20).all()
        record_audit(db,actor,"crm.read",{"count":len(leads)})
        return {"response":"Найдены доступные заявки.","actions":[{"tool":"crm.read","count":len(leads)}],"data":[{"id":x.id,"name":x.name,"request":x.request,"status":x.status} for x in leads]}
    if tool=="crm.create_note":
        require(actor,"crm.write")
        try: args=NoteArguments.model_validate(selected.get("arguments",{}))
        except Exception as exc: raise HTTPException(422,"Invalid tool arguments") from exc
        approval=Approval(actor=actor,action=tool,payload=args.model_dump(),status="pending")
        db.add(approval); db.commit(); db.refresh(approval)
        record_audit(db,actor,"write_requires_approval",{"approval_id":approval.id,"tool":tool})
        return {"response":"Подготовлено демонстрационное действие; требуется подтверждение администратора.","approval_id":approval.id,"executed":False}
    raise HTTPException(403,"Unknown tool")
@app.get("/audit")
def audit(db:Session=Depends(get_db),actor:str=Depends(user_from_token)):
    require(actor,"audit.read")
    return [{"actor":x.actor,"action":x.action,"detail":x.detail,"created_at":x.created_at} for x in db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(100)]
@app.post("/approvals/{approval_id}")
def decide_secure(approval_id:str,body:ApprovalDecision,db:Session=Depends(get_db),actor:str=Depends(user_from_token)):
    require(actor,"approval.decide")
    item=db.get(Approval,approval_id)
    if not item or item.action!="crm.create_note": raise HTTPException(404,"Approval not found")
    if item.status!="pending": raise HTTPException(409,"Approval already decided")
    item.status="approved" if body.approved else "rejected"; db.commit()
    record_audit(db,actor,"approval_decided",{"approval_id":item.id,"status":item.status,"execution":"mock only"})
    return {"approval_id":item.id,"status":item.status,"executed":False}
