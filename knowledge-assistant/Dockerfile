FROM node:20-alpine AS web-build
WORKDIR /web
COPY web/package.json ./package.json
RUN npm install
COPY web/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY pyproject.toml .
COPY app ./app
COPY --from=web-build /web/dist ./web/dist
RUN pip install --no-cache-dir .
EXPOSE 10000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8001}"]
