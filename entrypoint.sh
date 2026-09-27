#!/bin/sh
set -e

echo "==> Застосування міграцій Alembic..."
uv run alembic upgrade head

echo "==> Запуск вебсервера Uvicorn..."
exec uv run uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8000}"
