FROM python:3.14-slim

# Встановлення менеджера uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

# 1. Кешування шару залежностей
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

# 2. Явне копіювання скрипту запуску та надання прав
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

# 3. Копіювання решти вихідного коду проєкту
COPY . .

# 4. Відкриття порту
EXPOSE 8000

# 5. Єдина команда старту (вимоги Render виконано, жодних ланцюжків у CMD)
CMD ["./entrypoint.sh"]
