FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml .
COPY main.py ./main.py
COPY sandbox.py ./sandbox.py
COPY mcp_server.py ./mcp_server.py
COPY shared ./shared
COPY apps ./apps
COPY sample_data ./sample_data
RUN pip install --no-cache-dir .
RUN mkdir -p /app/data/uploads && useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app/data
USER appuser
EXPOSE 8000
CMD ["sh","-c","exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
