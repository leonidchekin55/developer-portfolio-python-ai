# Developer Portfolio — Python Backend & Applied AI

Два демонстрационных проекта, которые показывают разработку API и прикладной AI от локального запуска до наблюдаемости.

| Проект | Что показывает | Локальный запуск |
|---|---|---|
| [Pulseboard API](./pulseboard-api/) | SaaS API, JWT/RBAC, PostgreSQL, фоновые задачи, webhook idempotency, WebSocket events, Prometheus | `docker compose up --build` |
| [Knowledge Assistant](./knowledge-assistant/) | загрузка документов, RAG, Qdrant, Ollama, источники, история диалогов, React UI | `docker compose up --build` |

Оба проекта включают `.env.example`, демо-данные, health checks, миграции и GitHub Actions. См. README каждого проекта для архитектуры, API примеров и ограничений демо-режима.

## Render

В корне находится [render.yaml](./render.yaml) для развёртывания обоих проектов, общей PostgreSQL/Redis, Qdrant и Ollama. Инструкция и требования — в [Render deployment guide](./RENDER.md).
