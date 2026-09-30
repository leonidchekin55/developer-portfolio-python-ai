from importlib import import_module
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from shared.core import init_db
@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield
app=FastAPI(title="AI Engineer Portfolio",description="Six standalone demo APIs. Open a numbered path for each app's Swagger UI.",version="0.1.0",lifespan=lifespan)
modules=[("01-lead-manager","apps.01_lead_manager.main"),("02-knowledge-base","apps.02_knowledge_base.main"),("03-document-processor","apps.03_document_processor.main"),("04-evals","apps.04_evals.main"),("05-production","apps.05_production.main"),("06-secure-agent","apps.06_secure_agent.main")]
for prefix,path in modules:
    child=import_module(path).app
    app.mount(f"/{prefix}",child,name=prefix)
@app.get("/",response_class=HTMLResponse)
def index():
    projects=[
      ("01","AI-менеджер заявок","Структурирует входящий запрос, сохраняет лид и готовит действие для ручного подтверждения.","01-lead-manager"),
      ("02","AI Knowledge Base","Ищет по документам, сочетает векторный и текстовый поиск и возвращает цитаты.","02-knowledge-base"),
      ("03","AI Document Processor","Пакетно извлекает текст из PDF, DOCX, TXT и Markdown, показывает статус обработки.","03-document-processor"),
      ("04","AI Benchmark / Evals","Запускает набор проверок и показывает качество, задержку, стоимость и трассировки.","04-evals"),
      ("05","Production & Observability","Показывает готовность приложения, состояние базы и метрики запросов.","05-production"),
      ("06","Secure AI Agent","Демонстрирует роли, ограниченный набор инструментов, аудит и подтверждение действий.","06-secure-agent"),
    ]
    cards="".join(
      f'<article class="card"><div class="number">{number}</div><h2>{title}</h2><p>{description}</p>'
      f'<a class="button" href="/{slug}/docs">Открыть API</a>'
      +(f'<a class="text-link" href="/{slug}/demo">Открыть демо</a>' if number=="03" else "")
      +"</article>"
      for number,title,description,slug in projects
    )
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="description" content="Шесть демонстрационных проектов AI Engineer: агенты, RAG, обработка документов, evals и безопасность.">
<title>AI Engineer Portfolio · Леонид</title>
<style>
:root{{color-scheme:dark;--bg:#0b1020;--panel:#111a2d;--line:#27344c;--text:#eef4ff;--muted:#a9b7ca;--accent:#65e0bd;--blue:#91aaff}}
*{{box-sizing:border-box}}body{{margin:0;background:radial-gradient(ellipse at 15% 0%,#172849 0,transparent 38%),var(--bg);color:var(--text);font:16px/1.55 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}}
main{{width:min(1120px,100% - 40px);margin:0 auto;padding:64px 0 36px}}header{{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:52px}}
.brand{{font-size:14px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}}.status{{border:1px solid #326658;border-radius:999px;padding:7px 12px;color:var(--accent);font-size:13px}}
h1{{max-width:780px;margin:0;font-size:clamp(40px,7vw,72px);line-height:1.02;letter-spacing:-.055em}}.intro{{max-width:680px;margin:22px 0 34px;color:var(--muted);font-size:18px}}
.meta{{display:flex;flex-wrap:wrap;gap:10px;margin-bottom:36px}}.tag{{padding:6px 10px;border:1px solid var(--line);border-radius:8px;color:#c8d5e7;font-size:13px}}
.grid{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}}.card{{min-height:245px;padding:22px;background:linear-gradient(155deg,#141f34,#0f1728);border:1px solid var(--line);border-radius:16px;display:flex;flex-direction:column;align-items:flex-start}}
.number{{font:700 13px/1 ui-monospace,SFMono-Regular,Menlo,monospace;color:var(--accent)}}h2{{margin:15px 0 8px;font-size:20px;line-height:1.25;letter-spacing:-.02em}}.card p{{margin:0 0 20px;color:var(--muted);font-size:15px;flex:1}}
.button{{display:inline-flex;align-items:center;justify-content:center;text-decoration:none;color:#071a19;background:var(--accent);font-weight:700;padding:9px 13px;border-radius:8px;font-size:14px}}.button:hover{{background:#8bf0d2}}.text-link{{margin:10px 0 0;color:var(--blue);font-size:14px;text-decoration:none}}.text-link:hover{{text-decoration:underline}}
footer{{margin-top:30px;padding-top:20px;border-top:1px solid var(--line);color:#8998ad;font-size:13px}}footer a{{color:var(--blue)}}
@media(max-width:800px){{.grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}main{{padding-top:40px}}header{{margin-bottom:42px}}}}
@media(max-width:540px){{main{{width:min(100% - 28px,440px)}}.grid{{grid-template-columns:1fr}}.card{{min-height:210px}}.status{{font-size:12px}}}}
</style></head><body><main>
<header><div class="brand">Leonid · AI Engineer</div><div class="status">● Mock mode · без платных API</div></header>
<h1>Шесть проектов.<br>Одна инженерная база.</h1>
<p class="intro">Практическое портфолио на Python и FastAPI: от AI-агентов и поиска по знаниям до evals, безопасных действий и наблюдаемости.</p>
<div class="meta"><span class="tag">Python</span><span class="tag">FastAPI</span><span class="tag">PostgreSQL / SQLite</span><span class="tag">LLM tools · RAG · Evals</span></div>
<section class="grid" aria-label="Проекты портфолио">{cards}</section>
<footer>Демонстрационная среда: внешние действия не подключены; модель работает в mock-режиме. Для записи в API нужен токен владельца. Данные SQLite могут сброситься при перезапуске сервиса. <a href="/05-production/ready">Состояние сервиса</a></footer>
</main></body></html>"""
