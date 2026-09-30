import json,time,re
from collections import Counter
from pathlib import Path
from fastapi import Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy.orm import Session
from shared.core import create_app,get_db,EvalRun,user_from_token,settings
from shared.llm import complete
app=create_app("04 · AI Benchmark & Evals","Versioned dataset, repeatable model runs, reference overlap, estimated cost, latency and traces")
DATA=Path(__file__).with_name("dataset.json"); PROMPT_VERSION="v1.2"
# Editable pricing assumptions for gpt-4o-mini, USD per million tokens; label remains estimated.
PRICING={"gpt-4o-mini":(0.15,0.60)}
class RunRequest(BaseModel): models:list[str]=Field(default_factory=lambda:["mock"],min_length=1,max_length=5)
def tokens(text:str)->Counter:
    return Counter(re.findall(r"[\w]+",text.casefold(),flags=re.UNICODE))
def reference_f1(answer:str,expected:str)->float:
    predicted=tokens(answer); reference=tokens(expected)
    overlap=sum((predicted & reference).values())
    if not overlap: return 0.0
    precision=overlap/max(1,sum(predicted.values())); recall=overlap/max(1,sum(reference.values()))
    return round(2*precision*recall/(precision+recall),4)
def token_cost(model:str,usage:dict)->float|None:
    rates=PRICING.get(model)
    if not rates: return None
    input_tokens=usage.get("prompt_tokens",usage.get("input_tokens",0))
    output_tokens=usage.get("completion_tokens",usage.get("output_tokens",0))
    return round((input_tokens*rates[0]+output_tokens*rates[1])/1_000_000,8)
@app.get("/dataset")
def dataset(_:str=Depends(user_from_token)): return json.loads(DATA.read_text(encoding="utf-8"))
@app.post("/run")
def run(body:RunRequest,db:Session=Depends(get_db),actor:str=Depends(user_from_token)):
    if len(set(body.models))!=len(body.models): raise HTTPException(422,"Model list cannot contain duplicates")
    if any(not re.fullmatch(r"[A-Za-z0-9._:-]{1,80}",m) for m in body.models): raise HTTPException(422,"Invalid model identifier")
    if settings.llm_mode=="mock" and body.models!=["mock"]: raise HTTPException(422,"Select only mock while LLM_MODE=mock")
    if settings.llm_mode=="openai" and "mock" in body.models: raise HTTPException(422,"Select provider model IDs while LLM_MODE=openai")
    items=json.loads(DATA.read_text(encoding="utf-8")); results=[]
    try:
        for model in body.models:
            provider_model=None if model=="mock" else model
            for item in items:
                prompt=f"Answer using the provided support information. Prompt {PROMPT_VERSION}. {item['input']}"
                started=time.perf_counter(); output=complete(prompt,provider_model); latency=int((time.perf_counter()-started)*1000)
                answer=output["text"]; quality=reference_f1(answer,item["expected"])
                cost=0.0 if model=="mock" else token_cost(model,output.get("usage",{}))
                trace={"input":item["input"],"output":answer,"expected":item["expected"],"provider_model":output["model"],"prompt_version":PROMPT_VERSION,"estimated_cost_usd":cost,"usage":output.get("usage",{}),"cost_is_estimate":True}
                row=EvalRun(dataset=item["id"],model=model,prompt_version=PROMPT_VERSION,quality=quality,cost_usd=cost if cost is not None else 0.0,latency_ms=latency,trace=trace)
                db.add(row); db.flush()
                results.append({"id":row.id,"case":item["id"],"model":model,"quality_f1":quality,"estimated_cost_usd":cost,"latency_ms":latency,"trace":trace})
        db.commit()
    except Exception as exc:
        db.rollback()
        if isinstance(exc,HTTPException): raise
        raise HTTPException(502,"Model evaluation failed; no partial run was saved") from exc
    by_model=[]
    for model in body.models:
        group=[x for x in results if x["model"]==model]
        known_costs=[x["estimated_cost_usd"] for x in group if x["estimated_cost_usd"] is not None]
        by_model.append({"model":model,"cases":len(group),"mean_quality_f1":round(sum(x["quality_f1"] for x in group)/len(group),4),"estimated_cost_usd":round(sum(known_costs),8) if len(known_costs)==len(group) else None,"mean_latency_ms":round(sum(x["latency_ms"] for x in group)/len(group),1)})
    return {"count":len(results),"prompt_version":PROMPT_VERSION,"cost_note":"Cost is an estimate using the pricing assumptions in apps/04_evals/main.py; unknown models return null.","by_model":by_model,"results":results}
@app.get("/runs")
def runs(db:Session=Depends(get_db),_:str=Depends(user_from_token)):
    return [{"id":r.id,"dataset":r.dataset,"model":r.model,"prompt_version":r.prompt_version,"quality_f1":r.quality,"estimated_cost_usd":r.trace.get("estimated_cost_usd"),"latency_ms":r.latency_ms,"trace":r.trace} for r in db.query(EvalRun).order_by(EvalRun.created_at.desc()).limit(100)]
