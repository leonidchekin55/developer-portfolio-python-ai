from fastapi import Depends
from sqlalchemy import text
from shared.core import create_app,get_db,settings,user_from_token
app=create_app("05 · Production deployment","Production-oriented stack and operational diagnostics")
@app.get("/ready")
def ready(db=Depends(get_db)):
    db.execute(text("SELECT 1")); return {"status":"ready","database":"ok","llm_mode":settings.llm_mode}
@app.get("/ops/config")
def config(_:str=Depends(user_from_token)):
    return {"environment":settings.app_env,"llm_mode":settings.llm_mode,"database":"configured","secret_values":"never returned"}
