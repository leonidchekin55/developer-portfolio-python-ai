# Эксплуатация демо

Скопируйте `.env.example` в `.env`. Не храните production-секреты в Git; в CI/CD используйте хранилище секретов платформы. Смените `API_TOKEN`, пароль PostgreSQL и ключ LLM. `LLM_MODE=mock` оставляет вызовы локальными; `LLM_MODE=openai` использует `OPENAI_API_KEY`.

## Состояние и логи

`GET /05-production/ready` проверяет подключение к БД, `/05-production/metrics` отдаёт метрики запросов и задержки. `docker compose logs -f api` показывает логи сервиса. Healthchecks контролируют API, PostgreSQL и Redis; отдельный Celery worker обрабатывает очередь документов. В демо нет сборщика Prometheus/Grafana; `/metrics` отдаёт счётчик запросов и histogram задержек в формате Prometheus.

## HTTPS и reverse proxy

Nginx принимает HTTP на порту 8080. `apps/05_production/nginx.conf` задаёт proxy headers и лимит загрузки. Для публичного окружения добавьте TLS-сертификаты от выбранного ACME-клиента, TLS server block на 443, редирект HTTP→HTTPS и firewall; не публикуйте напрямую порт API/БД.

## Резервная копия и восстановление PostgreSQL

```bash
docker compose exec -T db pg_dump -U portfolio portfolio > backup.sql
docker compose exec db dropdb -U portfolio --if-exists --force portfolio
docker compose exec db createdb -U portfolio portfolio
cat backup.sql | docker compose exec -T db psql -U portfolio -d portfolio
```

Храните копии зашифрованными вне узла, задайте расписание и периодически проверяйте восстановление. Это инструкция, не настроенное автоматическое резервирование.
