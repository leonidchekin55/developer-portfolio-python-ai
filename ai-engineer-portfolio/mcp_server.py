"""Local stdio MCP server. It exposes only owner-scoped reads and draft creation."""
from mcp.server import MCPServer
from shared.core import SessionLocal,Lead,Approval,init_db
from shared.llm import classify_lead
from importlib import import_module
retrieve_documents=import_module("apps.02_knowledge_base.main").retrieve_documents

mcp=MCPServer("ai-engineer-portfolio",description="Local tools for the AI Engineer portfolio demos")
LOCAL_OWNER="demo-admin"

@mcp.tool()
def search_knowledge_base(question:str,top_k:int=3)->dict:
    """Search the local knowledge base and return excerpts with document citations."""
    if not question.strip() or len(question)>2000: return {"error":"question must contain 1–2000 characters"}
    if not 1<=top_k<=10: return {"error":"top_k must be between 1 and 10"}
    with SessionLocal() as db:
        return retrieve_documents(db,LOCAL_OWNER,question,top_k)

@mcp.tool()
def create_lead_draft(message:str)->dict:
    """Create a lead draft and pending approval; never contacts a CRM, email, or Sheets."""
    if not message.strip() or len(message)>5000: return {"error":"message must contain 1–5000 characters"}
    fields=classify_lead(message)
    with SessionLocal() as db:
        lead=Lead(owner=LOCAL_OWNER,name=fields["name"],contact=fields["contact"],request=fields["request"],budget=fields["budget"])
        db.add(lead); db.flush()
        approval=Approval(actor=LOCAL_OWNER,action="export_lead",payload={"lead_id":lead.id,"destination":"mock-crm-and-email","source":"mcp"})
        db.add(approval); db.commit()
        return {"lead_id":lead.id,"fields":fields,"approval_id":approval.id,"status":"pending","external_action_executed":False}

if __name__=="__main__":
    init_db()
    mcp.run(transport="stdio")
