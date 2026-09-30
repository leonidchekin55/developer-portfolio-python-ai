from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from shared.core import create_app, get_db, Lead, Approval, user_from_token
from shared.llm import classify_lead
app=create_app("01 · AI-менеджер заявок","Structured tool calling, validated extraction and human approval")
class Inbound(BaseModel):
    text:str=Field(min_length=3,max_length=5000)
    source:str=Field(default="web",min_length=1,max_length=40,pattern=r"^[a-zA-Z0-9_-]+$")
class Decision(BaseModel): approved:bool

def require_admin(actor:str):
    if actor!="demo-admin": raise HTTPException(403,"Admin role required")

@app.post("/leads/draft")
def draft(body:Inbound,db:Session=Depends(get_db),actor:str=Depends(user_from_token)):
    require_admin(actor)
    try: result=classify_lead(body.text)
    except Exception as exc: raise HTTPException(502,"Lead classification provider failed") from exc
    lead=Lead(owner=actor,name=result["name"],contact=result["contact"],request=result["request"],budget=result["budget"])
    db.add(lead); db.flush()
    approval=Approval(actor=actor,action="export_lead",payload={"lead_id":lead.id,"destination":"mock-crm-and-email","source":body.source})
    db.add(approval); db.commit()
    return {"lead":{"id":lead.id,"name":lead.name,"contact":lead.contact,"request":lead.request,"budget":lead.budget,"status":lead.status},"structured_output":result,"approval_required":approval.id,"tool_call":{"name":"export_lead","arguments":approval.payload,"external_action_executed":False,"note":"Requires approval; no external connector is configured."}}
@app.get("/leads")
def list_leads(db:Session=Depends(get_db),actor:str=Depends(user_from_token)):
    return [{"id":x.id,"name":x.name,"contact":x.contact,"request":x.request,"budget":x.budget,"status":x.status} for x in db.query(Lead).filter(Lead.owner==actor).order_by(Lead.created_at.desc()).limit(100)]
@app.get("/approvals")
def approvals(db:Session=Depends(get_db),actor:str=Depends(user_from_token)):
    q=db.query(Approval)
    if actor!="demo-admin": q=q.filter(Approval.actor==actor)
    return [{"id":a.id,"action":a.action,"payload":a.payload,"status":a.status} for a in q.order_by(Approval.created_at.desc()).limit(100).all()]
@app.post("/approvals/{approval_id}")
def decide(approval_id:str,body:Decision,db:Session=Depends(get_db),actor:str=Depends(user_from_token)):
    require_admin(actor)
    a=db.get(Approval,approval_id)
    if not a or a.action!="export_lead": raise HTTPException(404,"Approval not found")
    if a.status!="pending": raise HTTPException(409,"Approval already decided")
    a.status="approved" if body.approved else "rejected"; db.commit()
    return {"id":a.id,"status":a.status,"external_action_executed":False,"note":"Approval is recorded; no external connector is configured."}
