FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

FROM base AS builder

COPY uv.lock .
COPY pyproject.toml .

RUN uv pip install --system --no-cache --python /usr/local/bin/python3 -e .

FROM base AS final

WORKDIR /app

# Копируем установленные зависимости из этапа builder
# Финальный образ будет меньше - без uv и кеша pip/uv.
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Исключения в .dockerignore
COPY . .
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]