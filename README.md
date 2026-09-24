# Developer Portfolio — Python Backend & Applied AI

Два демонстрационных проекта, которые показывают разработку API и прикладной AI от локального запуска до наблюдаемости.

| Проект | Что показывает | Локальный запуск |
|---|---|---|
| [Pulseboard API](./pulseboard-api/) | SaaS API, JWT/RBAC, PostgreSQL, фоновые задачи, webhook idempotency, WebSocket events, Prometheus | `docker compose up --build` |
| [Knowledge Assistant](./knowledge-assistant/) | загрузка документов, RAG, Qdrant, Ollama, источники, история диалогов, React UI | `docker compose up --build` |

Оба проекта включают `.env.example`, демо-данные, health checks, миграции и GitHub Actions. См. README каждого проекта для архитектуры, API примеров и ограничений демо-режима.

## Render

Для бесплатного онлайн-демо используйте [render-free.yaml](./render-free.yaml): он создаёт два бесплатных веб-сервиса без платных баз, дисков, очередей или AI-моделей. Подробности и ограничения — в [Render deployment guide](./RENDER.md).

Полный локальный стек с PostgreSQL, Redis, Celery, Qdrant и Ollama запускается через Docker Compose из каждого проекта. Платный облачный вариант описан отдельно в [render.yaml](./render.yaml).
