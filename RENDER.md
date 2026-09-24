# Развёртывание на Render

`render.yaml` описывает оба проекта и их зависимости: два публичных API, Pulseboard worker, общие PostgreSQL и Redis, а также приватные Qdrant и Ollama. React UI встроен в Knowledge Assistant и отдаётся тем же доменом, что и API.

## Бесплатный демо-запуск

Бесплатный Blueprint `developer-portfolio-free` уже подключён к GitHub-репозиторию `leonidchekin55/developer-portfolio-python-ai`. Он разворачивает два сервиса: Pulseboard и Knowledge Assistant. Повторно создавать Blueprint не нужно.

Демо использует SQLite внутри бесплатного контейнера. При остановке или перезапуске Render локальные файлы удаляются, поэтому учётные записи и загруженные документы могут сброситься. Pulseboard выполняет демонстрационную задачу сразу и рассылает события в памяти одного процесса. Knowledge Assistant в облаке выполняет извлекающий поиск по текстовым фрагментам и показывает источники; генерация Ollama и Qdrant доступны в локальном полном режиме.

У бесплатных веб-сервисов Render общий лимит 750 часов на рабочее пространство и засыпание после 15 минут без запросов. Просыпание занимает около минуты. Это демо-режим, не production-хостинг.

## Публикация

1. Проверьте приватный репозиторий [developer-portfolio-python-ai](https://github.com/leonidchekin55/developer-portfolio-python-ai).
2. Откройте активный Blueprint [developer-portfolio-free в Render](https://dashboard.render.com/blueprint/exs-daqqpst9fdbs73c1b1tg).
3. Следите за новыми деплоями в Blueprint; актуальные адреса демо приведены в корневом README.

Render Blueprints создаются из подключённого Git-репозитория. После подключения Render может автоматически собирать новые коммиты в ветке Blueprint.

## Тарифы и хранение

PostgreSQL и Redis в Blueprint используют бесплатные планы. API, фоновый worker и приватные Qdrant/Ollama заданы на платных планах; для документов, векторов и файлов моделей Ollama выделены постоянные диски. Render тарифицирует compute и persistent disk отдельно; свободные сервисы без диска могут засыпать или иметь ограничения. Конфигурация Ollama CPU-only, поэтому генерация может быть медленной. Проверьте итоговую оценку в аккаунте Render перед нажатием Deploy. Текущие правила и тарифы: [Render pricing](https://render.com/pricing), [persistent disks](https://render.com/docs/disks).

## После запуска

- Knowledge Assistant: откройте его `onrender.com` адрес; `/docs` содержит API, `/health/ready` — статус готовности.
- Pulseboard API: `/docs`; имя демо-пользователя — `demo@pulseboard.local`. Пароль хранится в Render как сгенерированный секрет `DEMO_PASSWORD`, а не в коде.
- Для Pulseboard `SECRET_KEY`, `WEBHOOK_SECRET` и `DEMO_PASSWORD` Render генерирует автоматически.

Blueprint готовит демо-среду. Перед реальным использованием добавьте изоляцию пользователей в Knowledge Assistant и настройте политику удаления загруженных документов.
