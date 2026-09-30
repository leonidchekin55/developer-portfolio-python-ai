# Развёртывание на Render

`render.yaml` описывает оба проекта и их зависимости: два публичных API, Pulseboard worker, общие PostgreSQL и Redis, а также приватные Qdrant и Ollama. React UI встроен в Knowledge Assistant и отдаётся тем же доменом, что и API.

## Бесплатный демо-запуск

Бесплатный Blueprint `developer-portfolio-free` уже подключён к GitHub-репозиторию `leonidchekin55/developer-portfolio-python-ai`. Он разворачивает три сервиса: Pulseboard, Knowledge Assistant и портфолио из шести AI-проектов. Повторно создавать Blueprint не нужно.

Free Blueprint не создаёт managed PostgreSQL, Redis или persistent disks. Pulseboard использует демонстрационный режим с событиями в памяти. Knowledge Assistant использует SQLite в `/tmp` и extractive-поиск без внешнего LLM API. Аккаунты, документы и история временные и могут сброситься после перезапуска или деплоя; исходные файлы удаляются после индексации, извлечённый текст хранится в базе. AI-портфолио работает в mock-режиме. Платные API и инфраструктура не нужны.

У бесплатных веб-сервисов Render общий лимит 750 часов на рабочее пространство и засыпание после 15 минут без запросов. Просыпание занимает около минуты. Это демо-режим, не production-хостинг.

## Публикация

1. Проверьте приватный репозиторий [developer-portfolio-python-ai](https://github.com/leonidchekin55/developer-portfolio-python-ai).
2. Откройте активный Blueprint [developer-portfolio-free в Render](https://dashboard.render.com/blueprint/exs-daqqpst9fdbs73c1b1tg).
3. Следите за новыми деплоями в Blueprint; актуальные адреса демо приведены в корневом README.

Render Blueprints создаются из подключённого Git-репозитория. После подключения Render может автоматически собирать новые коммиты в ветке Blueprint.

## Тарифы и хранение

Полная конфигурация в `render.yaml` включает PostgreSQL и Redis, а также потенциально платные worker и приватные Qdrant/Ollama с постоянными дисками. Её не используйте для бесплатного демо. `render-free.yaml` запускает только публичные веб-сервисы на Free-плане, без внешней базы, очередей и persistent disks. Текущие правила и тарифы: [Render pricing](https://render.com/pricing), [persistent disks](https://render.com/docs/disks).

## После запуска

- Knowledge Assistant: откройте его `onrender.com` адрес; `/docs` содержит API, `/health/ready` — статус готовности. Данные демо временные.
- Pulseboard API: `/docs`; имя демо-пользователя — `demo@pulseboard.local`. Пароль хранится в Render как сгенерированный секрет `DEMO_PASSWORD`, а не в коде.
- AI Engineer Portfolio: `/sandbox` показывает все шесть сценариев без платных API.
- Для Pulseboard `SECRET_KEY`, `WEBHOOK_SECRET` и `DEMO_PASSWORD` Render генерирует автоматически.

Blueprint готовит демо-среду. В Knowledge Assistant уже реализованы учётные записи, изоляция документов и истории и удаление документов владельцем. Перед реальным использованием добавьте подтверждение email, восстановление пароля, объектное хранилище и резервное копирование.
