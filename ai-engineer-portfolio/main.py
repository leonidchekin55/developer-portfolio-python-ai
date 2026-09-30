from importlib import import_module
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from shared.core import init_db
from sandbox import router as sandbox_router
@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield
app=FastAPI(title="AI Engineer Portfolio",description="Six standalone demo APIs. Open a numbered path for each app's Swagger UI.",version="0.1.0",lifespan=lifespan)
app.include_router(sandbox_router)
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
      +f'<a class="text-link" href="/sandbox">Запустить интерактивное демо</a>'
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
<p><a class="button" href="/sandbox">Попробовать все 6 сценариев без регистрации</a></p>
<div class="meta"><span class="tag">Python</span><span class="tag">FastAPI</span><span class="tag">PostgreSQL / SQLite</span><span class="tag">LLM tools · RAG · Evals</span></div>
<section class="grid" aria-label="Проекты портфолио">{cards}</section>
<footer>Демонстрационная среда: внешние действия не подключены; модель работает в mock-режиме. Для записи в API нужен токен владельца. Данные SQLite могут сброситься при перезапуске сервиса. <a href="/05-production/ready">Состояние сервиса</a></footer>
</main></body></html>"""

@app.get("/sandbox",response_class=HTMLResponse,include_in_schema=False)
def sandbox_page():
    return HTMLResponse(SANDBOX_HTML,headers={"Cache-Control":"no-store","Referrer-Policy":"no-referrer","X-Content-Type-Options":"nosniff"})

SANDBOX_HTML = r'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="referrer" content="no-referrer"><meta name="description" content="Шесть изолированных AI Engineer сценариев в бесплатной mock-песочнице."><title>Интерактивное демо · Леонид</title><style>
:root{color-scheme:dark;--bg:#0b1020;--panel:#111a2d;--line:#27344c;--text:#eef4ff;--muted:#a9b7ca;--accent:#65e0bd;--blue:#91aaff}*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 15% 0%,#172849 0,transparent 38%),var(--bg);color:var(--text);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}main{width:min(1000px,calc(100% - 32px));margin:0 auto;padding:36px 0 60px}a{color:var(--blue)}header{display:flex;justify-content:space-between;gap:16px;align-items:center;margin-bottom:26px}.brand{font-size:13px;letter-spacing:.12em;text-transform:uppercase;color:var(--accent);font-weight:700}.safe{font-size:13px;color:var(--accent);border:1px solid #326658;border-radius:99px;padding:5px 10px}h1{font-size:clamp(34px,7vw,58px);line-height:1.03;letter-spacing:-.05em;margin:16px 0}p{color:var(--muted)}.notice{border:1px solid #315847;background:#10251f;padding:13px 16px;border-radius:12px;color:#c9f6e7}.grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:22px}.card{padding:20px;border:1px solid var(--line);border-radius:14px;background:linear-gradient(155deg,#141f34,#0f1728)}h2{font-size:19px;margin:0 0 7px}.card p{margin:0 0 14px;font-size:14px}label{display:block;font-size:13px;color:#c8d5e7;margin:10px 0 5px}input,textarea{display:block;width:100%;font:inherit;color:var(--text);background:#0a1221;border:1px solid #34435c;border-radius:8px;padding:10px}textarea{min-height:78px;resize:vertical}button{font:600 14px system-ui;border:0;border-radius:8px;padding:9px 13px;margin-top:12px;background:var(--accent);color:#071a19;cursor:pointer}button.secondary{background:#263550;color:var(--text);border:1px solid #40516e}button:disabled{opacity:.6;cursor:wait}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:330px;overflow:auto;background:#080e19;border:1px solid #26334a;color:#d7e3f4;padding:12px;border-radius:9px;font:12px/1.5 ui-monospace,monospace}.output{margin-top:10px}.approval button{margin-right:7px}.toolbar{display:flex;gap:10px;align-items:center;margin:18px 0}.error{color:#ffb4b4}@media(max-width:680px){.grid{grid-template-columns:1fr}header{align-items:flex-start;flex-direction:column}}
</style></head><body><main><header><a class="brand" href="/">← Leonid · AI Engineer</a><span class="safe">● Изолированное mock-демо</span></header><h1>Попробуйте все шесть проектов</h1><p>Сценарии выполняются на синтетических данных. API-ключи не нужны, введённый текст не сохраняется в рабочей базе; внешние CRM, почта и платные модели не вызываются.</p><div class="notice">Каждая сессия изолирована и автоматически удаляется через 30 минут. Не вводите реальные персональные, финансовые или конфиденциальные данные.</div><div class="toolbar"><span id="session">Создаём временную сессию…</span><button class="secondary" id="reset">Сбросить мои данные</button></div><section class="grid">
<article class="card"><h2>01 · AI-менеджер заявок</h2><p>Извлечение полей, JSON-структура и черновик действия с подтверждением.</p><label for="lead">Текст заявки</label><textarea id="lead">Нужен сайт до 100 тысяч рублей, срок — месяц</textarea><button data-run="01">Разобрать заявку</button><div class="output" id="out-01"></div></article>
<article class="card"><h2>02 · Knowledge Base</h2><p>Поиск по демо-корпусу, hybrid retrieval и цитата источника.</p><label for="question">Вопрос</label><input id="question" value="Какая база используется в Compose?"><label for="kbdoc">Добавить свой короткий текст (необязательно)</label><textarea id="kbdoc" placeholder="Например: тариф Pro стоит 20 000 рублей"></textarea><button data-run="02">Найти ответ</button><div class="output" id="out-02"></div></article>
<article class="card"><h2>03 · Document Processor</h2><p>Ограниченная обработка текста, статус задачи и результат.</p><label for="filename">Имя файла (.txt или .md)</label><input id="filename" value="sample.txt"><label for="document">Содержимое демонстрационного файла</label><textarea id="document">Инструкция: заявки обрабатываются в очереди, статусы доступны через API. Повторная обработка ограничена и безопасна.</textarea><button data-run="03">Обработать</button><div class="output" id="out-03"></div></article>
<article class="card"><h2>04 · AI Benchmark / Evals</h2><p>Небольшой локальный датасет, качество, задержка, стоимость и trace.</p><p>В этой песочнице используются только предсказуемые mock-ответы.</p><button data-run="04">Запустить eval</button><div class="output" id="out-04"></div></article>
<article class="card"><h2>05 · Production & Observability</h2><p>Снимок статуса, режима, безопасной сессии и счётчиков демо.</p><button data-run="05">Проверить состояние</button><div class="output" id="out-05"></div></article>
<article class="card"><h2>06 · Secure AI Agent</h2><p>Чтение синтетических CRM-данных, блокировка типовой prompt injection, подтверждение записи.</p><label for="agent">Запрос агенту</label><textarea id="agent">Покажи список заявок</textarea><button data-run="06">Выполнить безопасный сценарий</button><div class="output" id="out-06"></div></article>
</section><p><a href="/">Вернуться к витрине проектов</a> · <a href="/05-production/ready">Статус сервиса</a></p></main><script>
let sid=sessionStorage.getItem('portfolio_demo_session')||'';const statusEl=document.querySelector('#session');async function start(){if(!sid){const r=await fetch('/sandbox/session',{method:'POST'});if(!r.ok)throw Error('Не удалось создать сессию: '+r.status);const j=await r.json();sid=j.session_id;sessionStorage.setItem('portfolio_demo_session',sid)}statusEl.textContent='Временная сессия · данные только этой вкладки';}function show(target,obj){const box=document.querySelector('#out-'+target);box.replaceChildren();const pre=document.createElement('pre');pre.textContent=JSON.stringify(obj,null,2);box.append(pre);if(obj.approval_id){const controls=document.createElement('div');controls.className='approval';for(const [approved,title] of [[true,'Подтвердить демо-черновик'],[false,'Отклонить']]){const b=document.createElement('button');b.className='secondary';b.textContent=title;b.onclick=async()=>{b.disabled=true;try{const r=await fetch('/sandbox/approval/'+encodeURIComponent(obj.approval_id),{method:'POST',headers:{'Content-Type':'application/json','X-Demo-Session':sid},body:JSON.stringify({approved})});const j=await r.json();if(!r.ok)throw Error(j.detail||r.status);show(target,{...obj,decision:j})}catch(e){b.disabled=false;show(target,{error:e.message})}};controls.append(b)}box.append(controls)}}document.querySelectorAll('[data-run]').forEach(button=>button.addEventListener('click',async()=>{const id=button.dataset.run;let payload={};if(id==='01')payload.text=document.querySelector('#lead').value;if(id==='02'){payload.question=document.querySelector('#question').value;payload.text=document.querySelector('#kbdoc').value;payload.filename='visitor-note.txt'}if(id==='03'){payload.text=document.querySelector('#document').value;payload.filename=document.querySelector('#filename').value}if(id==='06')payload.text=document.querySelector('#agent').value;button.disabled=true;try{await start();const r=await fetch('/sandbox/run/'+id,{method:'POST',headers:{'Content-Type':'application/json','X-Demo-Session':sid},body:JSON.stringify(payload)});const j=await r.json();if(!r.ok)throw Error(j.detail||'HTTP '+r.status);show(id,j)}catch(e){show(id,{error:e.message})}finally{button.disabled=false}}));document.querySelector('#reset').onclick=async()=>{if(sid)await fetch('/sandbox/reset',{method:'POST',headers:{'X-Demo-Session':sid}});sessionStorage.removeItem('portfolio_demo_session');sid='';document.querySelectorAll('.output').forEach(x=>x.replaceChildren());try{await start()}catch(e){statusEl.textContent=e.message}};start().catch(e=>statusEl.textContent=e.message);
</script></body></html>'''
