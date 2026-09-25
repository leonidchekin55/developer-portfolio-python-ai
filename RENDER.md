# Развёртывание на Render

`render.yaml` описывает оба проекта и их зависимости: два публичных API, Pulseboard worker, общие PostgreSQL и Redis, а также приватные Qdrant и Ollama. React UI встроен в Knowledge Assistant и отдаётся тем же доменом, что и API.

## Бесплатный демо-запуск

Бесплатный Blueprint `developer-portfolio-free` уже подключён к GitHub-репозиторию `leonidchekin55/developer-portfolio-python-ai`. Он разворачивает два сервиса: Pulseboard и Knowledge Assistant. Повторно создавать Blueprint не нужно.

Free Blueprint не создаёт managed PostgreSQL, Redis или persistent disks. Pulseboard использует демонстрационный режим с событиями в памяти. Knowledge Assistant код поддерживает внешний PostgreSQL через `DATABASE_URL`, но подключение Supabase пока не прошло авторизацию и Render оставил последнюю успешную версию активной. Пока новый деплой не станет Live и `/health/ready` не подтвердит соединение, считайте состояние аккаунтов и истории временным. Исходные файлы удаляются после индексации; извлечённые тексты остаются в базе.

У бесплатных веб-сервисов Render общий лимит 750 часов на рабочее пространство и засыпание после 15 минут без запросов. Просыпание занимает около минуты. Это демо-режим, не production-хостинг.

## Публикация

1. Проверьте приватный репозиторий [developer-portfolio-python-ai](https://github.com/leonidchekin55/developer-portfolio-python-ai).
2. Откройте активный Blueprint [developer-portfolio-free в Render](https://dashboard.render.com/blueprint/exs-daqqpst9fdbs73c1b1tg).
3. Следите за новыми деплоями в Blueprint; актуальные адреса демо приведены в корневом README.

Render Blueprints создаются из подключённого Git-репозитория. После подключения Render может автоматически собирать новые коммиты в ветке Blueprint.

## Тарифы и хранение

Полная конфигурация в `render.yaml` включает PostgreSQL и Redis, а также платные worker и приватные Qdrant/Ollama с постоянными дисками. Это отдельный, потенциально платный вариант. Бесплатный Blueprint в `render-free.yaml` запускает только публичные веб-сервисы; Supabase подключается отдельно через секретную `DATABASE_URL`. Текущие правила и тарифы: [Render pricing](https://render.com/pricing), [persistent disks](https://render.com/docs/disks).

## После запуска

- Knowledge Assistant: откройте его `onrender.com` адрес; `/docs` содержит API, `/health/ready` — статус готовности.
- Pulseboard API: `/docs`; имя демо-пользователя — `demo@pulseboard.local`. Пароль хранится в Render как сгенерированный секрет `DEMO_PASSWORD`, а не в коде.
- Для Pulseboard `SECRET_KEY`, `WEBHOOK_SECRET` и `DEMO_PASSWORD` Render генерирует автоматически.

Blueprint готовит демо-среду. В Knowledge Assistant уже реализованы учётные записи, изоляция документов и истории и удаление документов владельцем. Перед реальным использованием добавьте подтверждение email, восстановление пароля, объектное хранилище и резервное копирование.
