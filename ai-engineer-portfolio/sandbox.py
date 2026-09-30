"""Public, isolated and deterministic portfolio sandbox; never calls external APIs."""
from __future__ import annotations

import re
import secrets
import threading
import time
from collections import Counter, deque
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict

from shared.core import settings
router = APIRouter(prefix="/sandbox", tags=["public sandbox"])
_lock = threading.RLock()
_sessions: dict[str, dict[str, Any]] = {}
_starts: dict[str, deque[float]] = {}
_boot = time.monotonic()
_MAX_SESSIONS = 500
_TTL = 30 * 60
_PER_MINUTE = 30
_SESSION_STARTS_PER_HOUR = 30

class DemoInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(default="", max_length=3000)
    question: str = Field(default="", max_length=500)
    filename: str = Field(default="sample.txt", max_length=100)
    approved: bool | None = None
    approval_id: str = Field(default="", max_length=80)

def _purge(now: float) -> None:
    for key in [key for key, value in _sessions.items() if now - value["seen"] > _TTL]:
        del _sessions[key]
    if len(_sessions) >= _MAX_SESSIONS:
        oldest = sorted(_sessions, key=lambda key: _sessions[key]["seen"])
        for key in oldest[:len(_sessions) - _MAX_SESSIONS + 1]:
            del _sessions[key]
    for peer in [peer for peer, starts in _starts.items() if not starts or now - starts[-1] > 3600]:
        del _starts[peer]

def _audit(state: dict[str, Any], event: dict[str, str]) -> None:
    state["audit"].append(event)

def _get_session(session_id: str | None) -> tuple[str, dict[str, Any]]:
    now = time.monotonic()
    with _lock:
        state = _sessions.get(session_id or "")
        if state is None or now - state["seen"] > _TTL:
            if session_id:
                _sessions.pop(session_id, None)
            raise HTTPException(401, "Демо-сессия истекла. Обновите страницу.")
        while state["calls"] and now - state["calls"][0] >= 60:
            state["calls"].popleft()
        if len(state["calls"]) >= _PER_MINUTE:
            raise HTTPException(429, "Лимит демо-запросов: 30 в минуту на сессию.")
        state["calls"].append(now)
        state["seen"] = now
        return session_id or "", state

def _require_mock() -> None:
    if settings.llm_mode != "mock":
        raise HTTPException(503, "Публичная песочница доступна только в безопасном mock-режиме.")

@router.post("/session")
def create_session(request: Request):
    now = time.monotonic()
    # Bound anonymous session creation by the ASGI peer address; never trust a caller-supplied X-Forwarded-For.
    peer = request.client.host if request.client else "unknown"
    with _lock:
        starts = _starts.setdefault(peer, deque())
        while starts and now - starts[0] > 3600:
            starts.popleft()
        if len(starts) >= _SESSION_STARTS_PER_HOUR:
            raise HTTPException(429, "Слишком много новых демо-сессий с этого подключения. Попробуйте позже.")
        starts.append(now)
        _purge(now)
        ident = secrets.token_urlsafe(32)
        _sessions[ident] = {"created": now, "seen": now, "calls": deque(), "leads": [], "documents": [],
                            "approvals": {}, "audit": deque(maxlen=100), "evals": 0}
    return {"session_id": ident, "expires_in_seconds": _TTL, "mode": "isolated mock", "external_actions": False}

@router.post("/run/{project}")
def run_demo(project: str, body: DemoInput, session_id: str | None = Header(default=None, alias="X-Demo-Session")):
    _require_mock()
    sid, state = _get_session(session_id)
    if project == "01":
        if len(body.text.strip()) < 3:
            raise HTTPException(422, "Опишите заявку (не менее 3 символов).")
        if len(state["leads"]) >= 20 or len(state["approvals"]) >= 20:
            raise HTTPException(429, "Лимит демо-черновиков в сессии достигнут; сбросьте её.")
        from shared.llm import classify_lead
        result = classify_lead(body.text.strip())
        approval_id = secrets.token_urlsafe(12)
        state["leads"].append({"id": secrets.token_hex(4), **result})
        state["approvals"][approval_id] = {"type": "lead_export", "status": "pending", "summary": "Передать синтетическую заявку в mock CRM"}
        _audit(state,{"action": "lead.draft", "result": "approval_required"})
        return {"scenario": "Структурирование заявки", "structured_output": result, "approval_id": approval_id,
                "approval_required": True, "external_action_executed": False,
                "connectors": ["mock CRM", "mock email", "mock Sheets"]}
    if project == "02":
        if body.text.strip():
            if len(body.text) > 3000: raise HTTPException(413, "Максимум 3000 символов на документ в демо.")
            if len(state["documents"]) >= 20: raise HTTPException(429, "В сессии уже 20 демо-документов; сбросьте её.")
            state["documents"].append({"filename": body.filename.rsplit("/", 1)[-1][:100], "text": body.text.strip()})
        question = body.question.strip()
        if len(question) < 2: raise HTTPException(422, "Введите вопрос к базе знаний.")
        corpus = [{"filename":"sample-handbook.txt", "text":"Демо-проект использует FastAPI и PostgreSQL. В локальном режиме применяется SQLite, а в Compose — PostgreSQL с pgvector. Mock-режим не вызывает платные API."}, *state["documents"]]
        terms = set(re.findall(r"[\w@.+-]+", question.casefold(), flags=re.UNICODE))
        # Tiny explicit demo synonym map improves Russian-language examples without pretending
        # that the public mock route is a pretrained semantic embedding model.
        if terms & {"база", "базу", "базы", "хранится", "хранилище"}:
            terms.update({"postgresql", "sqlite", "pgvector", "база", "базу", "базы"})
        hits=[]
        for doc in corpus:
            words = re.findall(r"[\w@.+-]+", doc["text"].casefold(), flags=re.UNICODE)
            common = terms & set(words)
            if common:
                score = round(len(common) / max(1, len(terms)), 3)
                hits.append({"filename":doc["filename"], "score":score, "citation":f"{doc['filename']} · демо-источник", "text":doc["text"][:800]})
        hits.sort(key=lambda hit:(-hit["score"], hit["filename"]))
        return {"scenario":"Hybrid retrieval + citations", "retrieval":"offline lexical demo; production API supports vector + lexical retrieval", "results":hits[:3], "citations":[hit["citation"] for hit in hits[:3]], "answer":"\n\n".join(hit["text"] for hit in hits[:3]) if hits else "В демо-корпусе совпадений не найдено."}
    if project == "03":
        if not body.text.strip(): raise HTTPException(422, "Добавьте текст документа.")
        if len(body.text) > 3000: raise HTTPException(413, "Максимум 3000 символов в публичном демо.")
        filename = body.filename.rsplit("/", 1)[-1]
        if not filename.lower().endswith((".txt", ".md")): raise HTTPException(415, "Публичная песочница принимает только TXT/MD текст.")
        if len(state["documents"]) >= 20: raise HTTPException(429, "В сессии уже 20 демо-документов; сбросьте её.")
        ident=secrets.token_hex(6)
        item={"id":ident,"filename":filename,"status":"processed","characters":len(body.text.strip()),"preview":body.text.strip()[:500]}
        state["documents"].append({"filename":filename,"text":body.text.strip()})
        return {"scenario":"Document processing", "queue":"isolated in-memory demo", "retries":0, "document":item, "persisted":False}
    if project == "04":
        cases=[("Про что проект?", "Проект использует FastAPI", "Проект использует FastAPI."),
               ("Какая база в Compose?", "В Compose используется PostgreSQL с pgvector", "В Compose используется PostgreSQL с pgvector."),
               ("Есть ли платный API?", "Mock-режим не вызывает платные API", "Mock-режим не вызывает платные API.")]
        results=[]
        for query, context, expected in cases:
            answer=context
            a=Counter(re.findall(r"\w+", answer.casefold())); e=Counter(re.findall(r"\w+", expected.casefold())); common=sum((a&e).values())
            precision=common/max(1,sum(a.values())); recall=common/max(1,sum(e.values()))
            results.append({"input":query,"answer":answer,"reference":expected,"quality_f1":round(2*precision*recall/max(1e-12,precision+recall),3),"latency_ms":0,"estimated_cost_usd":0.0,"trace":{"prompt_version":"sandbox-v1","provider":"deterministic mock"}})
        state["evals"] += 1
        return {"scenario":"Offline eval run", "model":"mock", "cases":len(results), "mean_quality_f1":round(sum(r["quality_f1"] for r in results)/len(results),3), "estimated_cost_usd":0.0,"results":results,"saved":False}
    if project == "05":
        return {"scenario":"Production readiness snapshot", "status":"ready", "database":"isolated sandbox memory", "llm_mode":"mock", "external_calls":False, "session_age_seconds":round(time.monotonic()-state["created"]), "uptime_seconds":round(time.monotonic()-_boot), "session_records":{"lead_drafts":len(state["leads"]),"documents":len(state["documents"]),"audit_events":len(state["audit"]),"eval_runs":state["evals"]}, "secrets":"not exposed"}
    if project == "06":
        message=body.text.strip()
        if not message: raise HTTPException(422, "Введите запрос агенту.")
        normalized=" ".join(message.casefold().split())
        if any(re.search(p, normalized) for p in (r"ignore\s+(all\s+)?(previous|prior|system)\s+instructions", r"reveal\s+(the\s+)?system\s+prompt", r"игнорируй\s+(все\s+)?(предыдущие|системные)\s+инструкции", r"раскрой\s+(системный\s+)?промпт")):
            _audit(state,{"action":"blocked_prompt_injection","result":"blocked"})
            return {"scenario":"Secure agent", "blocked":True, "response":"Запрос заблокирован демо-политикой безопасности.", "actions":[], "audit_recorded":True}
        if any(word in normalized for word in ("создай", "отправь", "измени", "удали", "create", "send", "update", "delete")):
            if len(state["approvals"]) >= 20: raise HTTPException(429,"Лимит черновиков в сессии достигнут; сбросьте её.")
            approval_id=secrets.token_urlsafe(12)
            state["approvals"][approval_id]={"type":"secure_write","status":"pending","summary":message[:300]}
            _audit(state,{"action":"write_requires_approval","result":"pending"})
            return {"scenario":"Secure agent", "blocked":False, "approval_required":True, "approval_id":approval_id, "executed":False, "allowed_tools":["crm.read", "crm.create_note (approval required)"]}
        _audit(state,{"action":"crm.read","result":"synthetic records"})
        return {"scenario":"Secure agent", "blocked":False,"response":"Показаны только синтетические записи песочницы.","actions":[{"tool":"crm.read","count":1}],"data":[{"id":"sample-001","name":"Демо-клиент","request":"Автоматизировать обработку заявок","status":"new"}],"role":"reader; writes require approval"}
    raise HTTPException(404, "Проект должен быть от 01 до 06.")

@router.post("/approval/{approval_id}")
def decide(approval_id: str, body: DemoInput, session_id: str | None = Header(default=None, alias="X-Demo-Session")):
    _require_mock()
    _, state = _get_session(session_id)
    approval=state["approvals"].get(approval_id)
    if not approval: raise HTTPException(404,"Черновик не найден в этой демо-сессии.")
    if approval["status"] != "pending": raise HTTPException(409,"Решение уже принято.")
    if body.approved is None: raise HTTPException(422,"Укажите approved: true/false.")
    approval["status"]="approved" if body.approved else "rejected"
    _audit(state,{"action":"approval_decided","result":approval["status"]})
    return {"status":approval["status"],"external_action_executed":False,"note":"Демо фиксирует решение, но ничего не отправляет и не изменяет во внешних системах."}

@router.post("/reset")
def reset(session_id: str | None = Header(default=None, alias="X-Demo-Session")):
    if not session_id: raise HTTPException(401,"Демо-сессия не найдена.")
    with _lock:
        _sessions.pop(session_id, None)
    return {"reset":True,"note":"Данные этой сессии удалены из памяти процесса."}
