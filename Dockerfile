FROM python:3.14-slim

# Встановлення менеджера uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# 1. Кешування шару залежностей
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# 2. Копіювання вихідного коду проєкту
COPY . .

# 3. Надання прав на виконання скрипту запуску після копіювання
RUN chmod +x entrypoint.sh

# 4. Відкриття порту
EXPOSE 8000

# 5. Запуск через оболонку sh (гарантований старт незалежно від вихідної ОС)
CMD ["sh", "./entrypoint.sh"]
