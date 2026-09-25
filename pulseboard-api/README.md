# Pulseboard API

Для бесплатного облачного демо используйте корневой `render-free.yaml`: SQLite, немедленная обработка демо-задач и события в памяти. Полная конфигурация с PostgreSQL, Redis и Celery запускается через Docker Compose ниже.

Публичная доска портфолио использует только `/api/v1/demo/*`: её подписанный краткоживущий токен ограничен отдельной песочницей и не предоставляет доступ к OAuth2 аккаунту или tenant данным.

Мультиарендный SaaS backend для управления проектами и задачами с журналом событий. Демонстрирует практики production-oriented API: изоляцию tenant-данных, роли, миграции, фоновые задачи, повторяемую обработку webhook и метрики.

## Стек

FastAPI · Pydantic v2 · SQLAlchemy 2 async · PostgreSQL · Alembic · Redis · Celery · JWT · Prometheus · Docker Compose.

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

API: <http://localhost:8000/docs>, health: `/health/live`, readiness: `/health/ready`, метрики: `/metrics`, Grafana: <http://localhost:3000> (`admin` / `admin`). При первом старте загружается demo tenant и пользователь `demo@pulseboard.local` / `ChangeMe123!`. Замените секреты перед любым внешним размещением.

## API

- `POST /api/v1/demo/session` — создаёт отдельную краткоживущую сессию публичной доски без доступа к основной базе SaaS.
- `GET /api/v1/demo/board` — список проектов и задач демо-сессии.
- `POST /api/v1/demo/projects`, `POST /api/v1/demo/tasks`, `PATCH /api/v1/demo/tasks/{id}` — изменение данных внутри одной демо-сессии.
- `POST /api/v1/demo/reset` — начинает изолированную сессию с чистым примером. Данные публичной демо-доски хранятся в памяти процесса до двух часов; лимиты: 12 проектов и 80 задач на сессию, 12 сессий в час с одного IP. Рестарт бесплатного сервиса очищает сессии.

- `POST /api/v1/auth/token` — OAuth2 password flow; возвращает access JWT.
- `GET /api/v1/me` — текущий пользователь.
- `GET/POST /api/v1/projects` — проектный каталог (`owner`, `member`, `viewer`).
- `GET/POST /api/v1/tasks` — задачи текущего tenant; создание ставит Celery уведомление и публикует событие.
- `POST /api/v1/webhooks/demo` — HMAC-SHA256 signature в `X-Signature`, `Idempotency-Key` обязателен; одинаковые ключи обрабатываются один раз.
- `WS /api/v1/events?token=<JWT>` — события текущего tenant.

### Webhook пример

```bash
BODY='{"event":"invoice.paid","external_id":"inv_demo_42"}'
SIG=$(printf %s "$BODY" | openssl dgst -sha256 -hmac "$WEBHOOK_SECRET" -hex | sed 's/^.* //')
curl -X POST localhost:8000/api/v1/webhooks/demo \
  -H 'Content-Type: application/json' -H 'Idempotency-Key: evt_demo_42' \
  -H "X-Signature: $SIG" -d "$BODY"
```

## Архитектура

`app/api` содержит транспорт и зависимости авторизации; `app/services` — правила доступа и доменные сценарии; `app/models`/`schemas` разделяют persistence и контракт; `app/tasks` — фоновые задачи; `app/core` — конфигурацию, JWT, логи и метрики. Alembic — единственный путь схемных изменений. WebSocket события проксируются через Redis Pub/Sub и фильтруются по tenant. Celery использует Redis broker.

## Разработка и проверки

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'
pytest
```

GitHub Actions проверяет форматирование, линт и pytest. Структура содержит тесты unit/service и API с SQLite; `docker compose` предназначен для интеграционного запуска. Добавляйте миграции через `alembic revision --autogenerate -m 'description'`, затем проверяйте SQL вручную.

## Мониторинг

Prometheus scrape `api:8000/metrics`; готовые дашборды и правила alerting можно добавить в Grafana. В комплекте есть provisioning datasource и обзорный dashboard. `/health/ready` проверяет PostgreSQL и Redis. Логи JSON в production mode.

## Перед реальным production

Установите уникальные секреты, включите TLS и secure cookies/headers на reverse proxy, храните refresh-токены с ротацией, настройте rate limiting, резервное копирование, очереди dead-letter и алерты. Демо-авторизация не заменяет полноценную систему управления аккаунтами.
