# AI Engineer Portfolio · Леонид

Единый локально запускаемый набор из шести проектов. Стек: Python 3.11+, FastAPI, SQLAlchemy, PostgreSQL, Docker Compose. Внешний LLM выключен по умолчанию: mock-режим не требует ключей и платных сервисов. OpenAI chat и embeddings подключаются независимо через `.env`; без ключа работают локальные mock/hash режимы.

> Это учебные демонстрационные приложения. CRM, почта и Google Sheets представлены mock-коннектором; нельзя считать их подключёнными к реальным сервисам. В Docker Compose обработка документов идёт через Redis + Celery worker с поздним ack и повтором при временных ошибках БД. При запуске без Docker используется локальная in-process обработка; она не переживает рестарт.

## Быстрый запуск

```bash
cp .env.example .env
# Требуется Docker с Compose

docker compose up --build
```

API через прокси: `http://localhost:8080`. Локально без контейнеров: Python 3.11+, `pip install -e '.[test]'`, затем `uvicorn main:app --reload`. SQLite используется без Docker; для Compose применяется PostgreSQL. База создаётся автоматически при запуске. Swagger каждой демки доступен по адресу `/01-lead-manager/docs` … `/06-secure-agent/docs`.

Демо-токены: `demo-token-change-me` (admin) и `reader-token` (reader; только чтение). Задавайте `Authorization: Bearer demo-token-change-me`. В production приложение откажется запускаться с demo-токенами: задайте два разных токена по 32+ символа и сильный `POSTGRES_PASSWORD`; секреты не коммитьте.

## Render: бесплатная демо-конфигурация

В корне лежит `render.yaml` для одного Render Web Service с планом `free`. Он запускает все шесть демо под разными путями, использует mock LLM и локальную SQLite в `/tmp`; платные API, базы, Redis, workers и persistent disks не создаются. В деплое используются случайные admin/reader токены: они хранятся в Render как секреты, а Blueprint задаёт `generateValue`.

Бесплатный сервис Render засыпает при простое, а его файловая система временная: записи, загруженные документы и SQLite могут сброситься при перезапуске или новом деплое. Не загружайте реальные персональные или конфиденциальные данные. В Render Dashboard проверьте, что сервис остаётся на плане **Free**; не выбирайте upgrade. См. [ограничения бесплатного тарифа Render](https://render.com/docs/free).

Публичная ссылка добавлена в основное портфолио `leonid-portfolio`. Перед повторным деплоем проверяйте `/`, `/sandbox`, `/05-production/ready` и `/01-lead-manager/docs`.

Опубликованное демо: [витрина шести проектов](https://leonid-ai-engineer-portfolio.onrender.com/), [интерактивная песочница всех шести проектов](https://leonid-ai-engineer-portfolio.onrender.com/sandbox), [Lead Manager API](https://leonid-ai-engineer-portfolio.onrender.com/01-lead-manager/docs), [Document Processor UI](https://leonid-ai-engineer-portfolio.onrender.com/03-document-processor/demo).

### Публичная демо-песочница

Страница `/sandbox` позволяет без токена пройти все шесть коротких сценариев. Она выдаёт случайный временный идентификатор сессии, хранит демонстрационные записи только в памяти процесса, ограничивает сессию 30 запросами в минуту и удаляет её после 30 минут бездействия. Для защиты от злоупотребления создание ограничено десятью сессиями в час на сетевой адрес. Кнопка сброса удаляет данные текущей сессии сразу. На Render используется только `LLM_MODE=mock`; публичные маршруты дополнительно отказываются работать при другом режиме, поэтому не могут вызвать платную модель. Публичный обработчик документов принимает только короткий TXT/MD текст; полный API с PDF/DOCX остаётся за bearer-токеном. Ни один сценарий песочницы не пишет в SQL, Redis, CRM, email или Google Sheets.

Публичный сценарий поиска работает на небольшом встроенном корпусе, текстовом совпадении и коротком списке русских синонимов. Он нужен для показа потока и цитат, а не является pretrained semantic search. Полная API-демонстрация поддерживает настроенный embedding backend и гибридный поиск; offline hash embeddings также не являются семантической моделью.

Для защищённых операций из Swagger нужен `API_TOKEN` из локального игнорируемого файла `.render-demo.env`; соответствующее значение хранится как секрет Render. Не публикуйте токен и не помещайте его в HTML сайта. Публичная витрина и Swagger доступны без авторизации; операции записи защищены bearer-токеном.

## Приложения

1. **AI-менеджер заявок** — структурирует обращение, сохраняет лид и создаёт предложение tool-call на mock CRM/email; экспорт требует решения человека. `POST /01-lead-manager/leads/draft`, `GET /01-lead-manager/approvals`, `POST /01-lead-manager/approvals/{id}`.
2. **Knowledge Base** — multi-user загрузка текста, chunking с overlap, поиск с источниками и ограничением доступа владельцем. `POST /02-knowledge-base/documents`, `POST /02-knowledge-base/search`. Поиск — гибридный vector + lexical retrieval с цитатами. Compose использует PostgreSQL/pgvector + HNSW; автономный локальный режим использует детерминированный feature hashing. Для семантических embeddings можно явно включить `EMBEDDING_MODE=openai` и задать ключ; offline hash-векторы не являются pretrained semantic model. PDF/DOCX извлечение показано в проекте 3.
3. **Document Processor** — batch PDF/DOCX/TXT/MD, извлечение текста, статусы и повторный безопасный вызов worker. `POST /03-document-processor/batch`, `GET /03-document-processor/documents/{id}`, `POST /03-document-processor/documents/{id}/retry`, UI `/03-document-processor/demo`. В Docker Compose используется Redis/Celery; локально без Docker — in-process background task. API возвращает `202`, предоставляет статусы/retry, ограничения размера файла, повтор при временных ошибках БД и защиту worker от параллельного повторного выполнения. Redis-постановка остаётся учебной и не обещает exactly-once.
4. **Benchmark/Evals** — небольшой версионированный dataset с вопросами и контекстом, несколько model-конфигураций, сохранённые trace, reference token F1, оценка стоимости и задержка. Mock отвечает по контексту без внешнего API; token-F1 — простая эвристическая метрика, не полноценная экспертная оценка. Стоимость оценочная, для неизвестных моделей выводится null. `GET /04-evals/dataset`, `POST /04-evals/run`, `GET /04-evals/runs`.
5. **Production deployment** — Compose с PostgreSQL/pgvector, Redis/Celery, Nginx, healthchecks, non-root контейнером, readiness `/05-production/ready` и Prometheus-метриками `/05-production/metrics` (через Nginx на порту 8080). См. `apps/05_production/nginx.conf`, `../.github/workflows/ci.yml` (CI монорепозитория), `docs/OPERATIONS.md`.
6. **Secure Agent** — роли, фиксированный набор инструментов, фильтр типовых injection-команд, валидация аргументов, аудит, одобрение записывающих действий. В `mcp_server.py` есть локальный stdio MCP server с поиском базы и созданием черновика заявки. `POST /06-secure-agent/agent`, `POST /06-secure-agent/approvals/{id}`, `GET /06-secure-agent/audit`. MCP запускайте отдельно через `python mcp_server.py` (stdio, локальный процесс; сетевой доступ не открыт). Защита от prompt injection демонстрационная и не гарантирует обнаружение всех атак.

## Примеры HTTP

```bash
export BASE=http://localhost:8080
export TOKEN=demo-token-change-me
curl -s "$BASE/01-lead-manager/health"
curl -s -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"text":"Нужен сайт до 100 тысяч рублей, свяжитесь по leonid@example.org"}' \
  "$BASE/01-lead-manager/leads/draft"
curl -s -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"text":"Условия оплаты: пакет Pro стоит 20 000 рублей в месяц."}' \
  "$BASE/02-knowledge-base/documents"
curl -s -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"question":"Сколько стоит пакет Pro?"}' "$BASE/02-knowledge-base/search"
curl -s -H "Authorization: Bearer $TOKEN" -F 'files=@sample_data/handbook.txt' "$BASE/03-document-processor/batch"
curl -s -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"models":["mock"]}' "$BASE/04-evals/run"
curl -s -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"message":"Создай заметку: перезвонить клиенту"}' "$BASE/06-secure-agent/agent"
```

## Подключение MCP

MCP сервер использует официальный [Python SDK](https://github.com/modelcontextprotocol/python-sdk) и запускается отдельным локальным stdio-процессом. Он предоставляет два инструмента: поиск с цитатами и создание черновика заявки с pending approval; сетевой MCP transport не включён.

Пример блока для MCP host (замените пути на абсолютные пути к своему checkout и Python окружению):

```json
{
  "mcpServers": {
    "ai-engineer-portfolio": {
      "command": "/ABS/PATH/ai-engineer-portfolio/.venv/bin/python",
      "args": ["/ABS/PATH/ai-engineer-portfolio/mcp_server.py"],
      "env": {
        "DATABASE_URL": "sqlite:////ABS/PATH/ai-engineer-portfolio/portfolio.db",
        "LLM_MODE": "mock"
      }
    }
  }
}
```

## Архитектура

```mermaid
flowchart LR
  U[Web / Telegram / curl] --> N[Nginx]
  N --> F[FastAPI apps]
  F --> S[Shared services: auth, LLM adapter, audit]
  S --> P[(PostgreSQL + pgvector)]
  F --> R[(Redis + Celery queue)]
  F --> L[Mock LLM + local hash embeddings]
  L -. optional API key .-> O[OpenAI chat + embeddings]
  F --> A[Human approval]
```

```mermaid
sequenceDiagram
  participant C as Клиент
  participant API as Lead API
  participant LLM as Mock/LLM
  participant DB as PostgreSQL
  participant H as Менеджер
  C->>API: обращение
  API->>LLM: классификация в структуру
  LLM-->>API: JSON поля лида
  API->>DB: лид + pending approval
  API-->>C: черновик + approval id
  H->>API: approve/reject
  API->>DB: статус решения + аудит
```

## Структура

```text
shared/                 общие настройки, БД, auth, LLM/mock, сущности
apps/01_lead_manager/   заявки, tool call proposal, approval
apps/02_knowledge_base/ загрузка, chunks, поиск, citations
apps/03_document_processor/ batch extraction + status
apps/04_evals/          dataset, runs, traces, metrics
apps/05_production/     readiness, metrics, nginx
apps/06_secure_agent/   роли, allowlist, approvals, audit
sample_data/            безопасные демонстрационные файлы
tests/                  интеграционные и unit tests
docs/                   эксплуатация и backup
```

## Дальше развивать с Codex/Claude

Откройте корень этого репозитория и попросите агента выполнить одну небольшую задачу за раз. В репозитории есть разделённые приложения и понятные интерфейсы, `.env.example`, тесты и локальный запуск. Просите агента сначала прочитать README и целевое приложение, затем менять его, запускать проверки и кратко перечислять затронутые файлы. Реальные ключи не вставляйте в промпты и коммиты.

## Проверки

В CI также собирается Docker image; запуск Compose на локальной машине требует запущенный Docker daemon.

```bash
pip install -e '.[test]'
pytest -q
```

## Что показывать первым

- **AI-менеджер заявок**: демонстрирует структурированный вывод, сохранение данных и human approval; честно называйте интеграции с CRM/email mock-коннекторами.
- **Document Processor**: показывает пакетную обработку форматов, статусы и устойчивую границу для внедрения очереди; укажите, что Compose использует Redis/Celery worker, а локальный запуск без Docker — in-process worker.
- **Evals**: хорошо раскрывает инженерный подход к оценке LLM — датасет, версии промптов, trace, стоимость и latency; подчёркивайте, что dataset маленький, а метрика quality эвристическая.

В резюме: «Разработал локальный прототип AI-обработки заявок на FastAPI/PostgreSQL: извлечение структурированных полей, сохранение лида и human-in-the-loop подтверждение mock-действия». Не заявляйте production-пользователей, бизнес-эффект, реальные CRM-интеграции или доказанную защищённость без отдельной реализации и измерений.
