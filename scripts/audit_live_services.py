#!/usr/bin/env python3
"""Read-only availability and API contract checks for all published demos."""
from __future__ import annotations
import json
import urllib.error
import urllib.request
SERVICES={
 "portfolio":("https://leonid-portfolio.onrender.com",("/","/pulseboard.html","/ai-engineer-tour.html","/assets/ai-engineer-portfolio-tour.srt","/assets/ai-engineer-portfolio-tour.mp4")),
 "pulseboard":("https://portfolio-pulseboard-demo.onrender.com",("/health/live","/health/ready","/docs","/openapi.json")),
 "knowledge":("https://portfolio-knowledge-demo.onrender.com",("/health/live","/health/ready","/docs","/openapi.json","/")),
 "ai_portfolio":("https://leonid-ai-engineer-portfolio.onrender.com",("/05-production/ready","/sandbox","/openapi.json")),
}
REQUIRED={"pulseboard":{"/api/v1/demo/session","/api/v1/demo/board","/api/v1/demo/projects","/api/v1/demo/tasks","/api/v1/demo/reset"},"knowledge":{"/api/v1/auth/register","/api/v1/auth/login","/api/v1/documents","/api/v1/chat"}}
def fetch(url:str,timeout:int=60):
 request=urllib.request.Request(url,headers={"User-Agent":"portfolio-live-audit/1.0","Accept":"*/*"})
 try:
  with urllib.request.urlopen(request,timeout=timeout) as response:return response.status,response.read(2_000_000),response.headers.get("content-type","")
 except urllib.error.HTTPError as error:return error.code,error.read(1000),error.headers.get("content-type","")
def check(condition:bool,message:str)->None:
 if not condition:raise RuntimeError(message)
 print("PASS",message,flush=True)
def main()->None:
 for name,(base,paths) in SERVICES.items():
  for path in paths:
   status,body,content_type=fetch(base+path)
   check(status==200,f"{name} {path} HTTP {status} ({content_type})")
   if path=="/05-production/ready":
    ready=json.loads(body);check(ready.get("status")=="ready" and ready.get("llm_mode")=="mock","AI portfolio ready and zero-cost mock mode")
   if path=="/openapi.json" and name in REQUIRED:
    actual=set(json.loads(body).get("paths",{}));missing=REQUIRED[name]-actual
    check(not missing,f"{name} OpenAPI contains required demo paths")
 print("All online service availability checks passed.",flush=True)
if __name__=="__main__":
 try:main()
 except Exception as error:raise SystemExit(f"FAIL {type(error).__name__}: {error}")
