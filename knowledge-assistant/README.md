# Knowledge Assistant

Корневой `render-free.yaml` включает бесплатный extractive-режим: документы сохраняются как текстовые фрагменты на время работы контейнера, поиск возвращает подходящие фрагменты и ссылки на страницы. Для генеративных ответов с embeddings, Qdrant и Ollama запустите полный локальный стек через Docker Compose ниже.

Локальный помощник по личным документам: загружает PDF/DOCX/TXT, извлекает текст, режет на перекрывающиеся фрагменты, индексирует в Qdrant и отвечает по найденным источникам. История диалогов хранится в PostgreSQL. Локальный режим использует Ollama (не требует API ключа).

## Стек и запуск

FastAPI · PostgreSQL · Qdrant · Redis · Celery · Ollama (`nomic-embed-text` + `llama3.2`) · React · Vite · Tailwind.

```bash
cp .env.example .env
docker compose up --build
```

Откройте <http://localhost:5173>. API docs: <http://localhost:8001/docs>. Первый старт может занять несколько минут: Ollama загружает модели. Затем загрузите документ и задайте вопрос. Если локальное железо ограничено, выберите меньшую Ollama-модель в `.env`.

Без Docker: Python 3.11+, Node 20+, PostgreSQL, Qdrant, Redis и Ollama; `pip install -e '.[dev]'`, `uvicorn app.main:app --reload --port 8001`; UI: `npm install && npm run dev` в `web/`.

## Поток данных

1. API проверяет расширение и размер файла (20 MB), извлекает текст через pypdf/python-docx.
2. Chunker формирует фрагменты с перекрытием; embedding-модель Ollama выдаёт векторы.
3. Qdrant хранит вектора и метаданные документа/страницы/индекса фрагмента.
4. Для вопроса API ищет top-k релевантных фрагментов, формирует grounded prompt и просит LLM отвечать только на основе контекста.
5. Ответ, вопрос и список источников сохраняются в истории PostgreSQL; клиент видит цитаты с именем файла и номером страницы.

## Endpoints

- `POST /api/v1/documents` multipart file upload
- `GET /api/v1/documents` список документов
- `POST /api/v1/chat` `{ "question": "..." }`
- `GET /api/v1/history?limit=20`
- `GET /health/live`, `/health/ready`

## Приватность и ограничения

Данные остаются в локальных контейнерах при использовании Ollama. Реализация рассчитана на локальное демо: нет пользовательских аккаунтов/изоляции, антивирусной проверки файлов или внешнего хранилища. Добавьте auth/tenant authorization и retention политики до публикации для реальных пользователей. Для production нужны лимиты на уровне reverse proxy, строгая очистка пользовательского ввода, защита от prompt injection, контроль затрат/очередей, трассировка retrieval качества и управляемое удаление векторов.
