# 🛡️ REST API Контактної книги (Contacts Management API)

[![Python Version](https://img.shields.io/badge/Python-3.14%2B-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0_(Async)-D71F00?style=flat&logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7_(Alpine)-DC382D?style=flat&logo=redis&logoColor=white)](https://redis.io/)
[![Pytest](https://img.shields.io/badge/Pytest-61_passed_|_90%25_cov-brightgreen?style=flat&logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![Sphinx](https://img.shields.io/badge/Docs-Sphinx_RTD-0A507A?style=flat&logo=sphinx&logoColor=white)](https://www.sphinx-doc.org/)
[![Docker Compose](https://img.shields.io/badge/Docker_Compose-v2-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![Package Manager](https://img.shields.io/badge/uv-Astral-DE5FE9?style=flat&logo=astral&logoColor=white)](https://github.com/astral-sh/uv)

Сучасний, швидкісний та асинхронний RESTful API сервіс для керування персональною контактною книгою. Застосунок побудовано на базі **FastAPI** та **SQLAlchemy 2.0 Async** із суворою багатошаровою архітектурою, повною ізоляцією контактів між користувачами, багаторівневою безпекою (пара JWT токенів access/refresh, верифікація email, скидання пароля), ролевою моделлю доступу (RBAC: `user` / `admin`), кешуванням у **Redis** з автоматичною інвалідацією, обмеженням частоти запитів (Rate Limiting) та хмарним збереженням медіа у **Cloudinary**.

---

## 🛠 Стек технологій та архітектура

### Базовий бекенд та шар даних (Core Backend & Data Layer)
- **Python 3.14+** — сучасна мова з підтримкою суворої асинхронності (asyncio) та оновленої типізації (PEP 585, PEP 604).
- **FastAPI 0.115+** — швидкісний вебфреймворк з автоматичною інтерактивною документацією OpenAPI (Swagger UI / ReDoc).
- **SQLAlchemy 2.0 (Async)** — асинхронна ORM із сучасним декларативним синтаксисом (`Mapped`, `mapped_column`, асинхронні сесії `async_sessionmaker`).
- **PostgreSQL 16** — надійна реляційна СУБД зі зв'язками зовнішніх ключів та каскадним видаленням даних.
- **psycopg 3 (Binary)** — високопродуктивний асинхронний драйвер підключення до PostgreSQL.
- **Pydantic v2 & Pydantic-Settings** — декларативна валідація схем даних, запитів, відповідей та конфігурації оточення.
- **Alembic** — асинхронні міграції структури бази даних.

### Безпека, кешування та пошта (Security, Cache & Mail)
- **JWT (python-jose)** — безпечна автентифікація з криптографічним підписом токенів (HS256):
  - `access_token` — короткоживучий токен доступу до API (30 хвилин);
  - `refresh_token` — довгоживучий токен оновлення сесії (1–7 днів);
  - одноразові токени для верифікації пошти та безпечного скидання пароля.
- **Passlib & Bcrypt** — надійне одностороннє соління та хешування паролів користувачів.
- **Redis 7 (Alpine)** — швидке in-memory кешування профілю поточного користувача (`current_user`) з автоматичним TTL та миттєвою інвалідацією при оновленнях.
- **FastAPI-Mail & Mailpit** — асинхронна відправка листів у фонових задачах (`BackgroundTasks`) із Jinja2 HTML-шаблонами (локальний SMTP-сервер Mailpit із власним Web UI).
- **SlowAPI** — захист чутливих маршрутів від перевантаження (Rate Limiting: 10 запитів/хв на профіль).
- **Cloudinary SDK** — хмарне збереження та оптимізація аватарів користувачів (кадрування 250×250 px, crop fill).
- **Role-Based Access Control (RBAC)** — розмежування прав (`user` / `admin`); зміна аватара дозволена виключно користувачам із роллю адміністратора.

### Інфраструктура, тестування та документація (Infra, Quality & Docs)
- **uv (Astral)** — блискавичний менеджер середовища та блокування залежностей (`uv.lock`).
- **Docker Compose v2** — повна оркестрація сервісів (`db`, `redis`, `mailpit`, `api`) у спільній мережі.
- **Pytest Suite** — 61 автоматизований тест (модульні та інтеграційні) із покриттям кодової бази **90%** (ізольована SQLite in-memory база, асинхронні моки Redis, пошти та хмари).
- **Sphinx & sphinx_rtd_theme** — автоматична компіляція повної технічної документації проєкту з Google-style docstrings.

---

## 🚀 Швидкий запуск (Quick Start)

### Спосіб 1. Запуск усього стеку в Docker (Рекомендовано)

Запуск усіх чотирьох сервісів (`PostgreSQL`, `Redis`, `Mailpit`, `FastAPI API`) виконується однією командою:

```bash
# 1. Створіть файл конфігурації оточення з шаблону:
cp .env.example .env

# 2. Запустіть весь стек у фоновому режимі з примусовою збіркою образу:
docker compose up -d --build
```

**Після старту доступні всі інтерфейси:**
- 🌐 **Swagger UI (Інтерактивне API):** [http://localhost:8000/docs](http://localhost:8000/docs)
- 🩺 **Перевірка здоров'я сервісу:** [http://localhost:8000/healthz](http://localhost:8000/healthz)
- 📬 **Mailpit Web UI (Перегляд листів):** [http://localhost:8025](http://localhost:8025)
- 🗄 **PostgreSQL:** порт `5432`
- ⚡ **Redis:** порт `6379`

Перегляд логів застосунку в реальному часі:
```bash
docker compose logs -f api
```

Зупинка та видалення контейнерів зі збереженням томів баз даних:
```bash
docker compose down
```

---

### Спосіб 2. Локальний запуск для розробки (Local Dev із uv)

```bash
# 1. Встановіть залежності проєкту у віртуальне середовище:
uv sync

# 2. Створіть та налаштуйте локальний .env файл:
cp .env.example .env

# 3. Підніміть допоміжну інфраструктуру в Docker:
docker compose up -d db redis mailpit

# 4. Застосуйте міграції Alembic до бази даних PostgreSQL:
uv run alembic upgrade head

# 5. Запустіть сервер розробки Uvicorn із гарячим перезавантаженням:
uv run uvicorn src.main:app --reload --port 8000
```

---

## 🧪 Чекліст тестування та верифікації

Усі сценарії та команди для комплексної перевірки працездатності, стабільності та якості кодової бази.

### 1. Модульне та інтеграційне тестування (Pytest & Coverage)

Проєкт містить **61 автономний тест** (unit-тести репозиторіїв та сервісів із моками, інтеграційні тести роутерів `auth`, `users`, `contacts`, RBAC-ролей та перевірки токенів).

Запуск усіх тестів із виведенням підсумкової таблиці покриття в консоль:
```bash
uv run pytest --cov=src --cov-report=term-missing -vv
```
> **Результат:** 61 passed, сумарне покриття кодової бази `src/` становить **90%**.

Генерація візуального інтерактивного HTML-звіту покриття:
```bash
uv run pytest --cov=src --cov-report=html
```
> Для перегляду детального HTML-звіту з кольоровою підсвіткою рядків відкрийте файл `htmlcov/index.html` напряму у вашому веббраузері.

---

### 2. Збірка та відкриття Sphinx-документації

Усі модулі, класи та функції проєкту задокументовані за стандартом Google-style docstrings.

Складання статичної документації у форматі HTML:
```bash
uv run sphinx-build -b html docs docs/_build/html
```
> Для перегляду скомпільованої технічної документації відкрийте файл `docs/_build/html/index.html` напряму у вашому веббраузері.

---

### 3. Перевірка працездатності через /healthz та Swagger UI

1. **Liveness / Readiness Probe:**
   Виконайте запит у терміналі або відкрийте у браузері:
   ```bash
   curl -s http://localhost:8000/healthz
   ```
   **Очікувана відповідь (HTTP 200 OK):**
   ```json
   {
     "status": "ok",
     "database": "ok"
   }
   ```
2. **Інтерактивна документація:**
   Перейдіть за посиланням [http://localhost:8000/docs](http://localhost:8000/docs) для перегляду та тестування всіх ендпоінтів через Swagger UI (або [http://localhost:8000/redoc](http://localhost:8000/redoc) для ReDoc).

---

### 4. Верифікація кешування та TTL у Redis

Під час запитів авторизованого користувача до захищених ендпоінтів (`/api/users/me`, робота з контактами) дані користувача кешуються у Redis, мінімізуючи повторні звернення до PostgreSQL.

1. **Перевірка зв'язку з сервером Redis:**
   ```bash
   docker compose exec redis redis-cli ping
   ```
   *Очікувана відповідь:* `PONG`

2. **Реєстрація тестового користувача та активація:**
   - У Swagger UI (`http://localhost:8000/docs`) виконайте запит `POST /api/auth/register`:
     ```json
     {
       "username": "john",
       "email": "john@example.com",
       "password": "Password123!"
     }
     ```
   - Відкрийте Mailpit Web UI ([http://localhost:8025](http://localhost:8025)), знайдіть лист та підтвердіть пошту переходом за посиланням або викликом `GET /api/auth/confirmed_email/{token}`.

3. **Авторизація та перевірка наявності ключів у кеші:**
   - Виконайте `POST /api/auth/login` (або натисніть кнопку **Authorize 🔓** у Swagger UI, ввівши логін `john@example.com` та пароль `Password123!`).
   - Виконайте запит `GET /api/users/me`.
   - Перевірте список закешованих ключів у Redis:
     ```bash
     docker compose exec redis redis-cli keys "user:*"
     ```
     *Приклад відповіді:* `1) "user:john@example.com"`

4. **Перевірка залишкового часу життя (TTL) кешу:**
   ```bash
   docker compose exec redis redis-cli ttl "user:john@example.com"
   ```
   *Приклад відповіді:* `(integer) 115` *(залишок часу життя запису в секундах)*.

5. **Перегляд закешованого JSON-об'єкта:**
   ```bash
   docker compose exec redis redis-cli get "user:john@example.com"
   ```

6. **Перевірка інвалідації кешу:**
   - При зміні пароля (`POST /api/auth/reset-password`) або оновленні аватара (`PATCH /api/users/avatar`) ключ автоматично видаляється з Redis, а наступний запит підвантажує свіжі дані з PostgreSQL.

---

### 5. Перевірка електронної пошти у Mailpit Web UI

Усі листи (підтвердження реєстрації та одноразові токени для скидання пароля) миттєво доставляються у локальний сервіс Mailpit.

1. Відкрийте вебінтерфейс перегляду листів: [http://localhost:8025](http://localhost:8025).
2. **Сценарій підтвердження пошти:**
   - Виконайте реєстрацію `POST /api/auth/register`.
   - У вікні Mailpit з'явиться лист із темою *"Підтвердження адреси електронної пошти"*.
   - Відкрийте лист і перейдіть за посиланням або скопіюйте токен для ендпоінта `GET /api/auth/confirmed_email/{token}`.
3. **Сценарій скидання пароля:**
   - Виконайте `POST /api/auth/forgot-password` із передачею вашого підтвердженого email.
   - У Mailpit надійде лист із посиланням та одноразовим токеном на скидання пароля.
   - Скопіюйте отриманий токен та виконайте `POST /api/auth/reset-password` із новим паролем.

---

### 6. Перевірка контролю доступу (RBAC) та обмеження запитів (Rate Limiting)

1. **Ролі користувачів (RBAC) та завантаження аватара:**
   - Спробуйте викликати `PATCH /api/users/avatar` під обліковим записом зі стандартною роллю `user` → сервер повертає статус **403 Forbidden** (*"Зміна аватара дозволена лише адміністраторам"*).
   - Під обліковим записом із роллю `admin` запит успішно завантажує зображення у Cloudinary зі статусом **200 OK**.
2. **Rate Limiting на ендпоінті профілю:**
   - Виконайте запит `GET /api/users/me` понад 10 разів протягом однієї хвилини.
   - На 11-му запиті сервер повертає статус **429 Too Many Requests** (*"Rate limit exceeded: 10 per 1 minute"*).

---

## 📋 Специфікація API (Маршрути)

### 🔐 Автентифікація та доступ (`auth`)

| Метод | Маршрут | Опис операції | Успішний статус | Очікувані помилки |
| :---: | :--- | :--- | :---: | :--- |
| **POST** | `/api/auth/register` | Реєстрація нового користувача та відправка листа верифікації | `201 Created` | `409 Conflict` (дублікат email/username), `422` |
| **POST** | `/api/auth/login` | Вхід у систему, повернення пари `access_token` та `refresh_token` | `200 OK` | `401 Unauthorized` (невірні дані або пошта не підтверджена) |
| **POST** | `/api/auth/refresh_token` | Оновлення пари токенів за валідним refresh-токеном | `200 OK` | `401 Unauthorized` (недійсний або протермінований токен) |
| **GET** | `/api/auth/confirmed_email/{token}` | Активація облікового запису за поштовим токеном | `200 OK` | `400 Bad Request`, `422 Unprocessable` |
| **POST** | `/api/auth/request_email` | Повторний запит листа для верифікації пошти | `200 OK` | `422 Unprocessable` |
| **POST** | `/api/auth/forgot-password` | Запит на скидання пароля (відправка листа з одноразовим токеном) | `200 OK` | `422 Unprocessable` |
| **POST** | `/api/auth/reset-password` | Встановлення нового пароля за токеном скидання та інвалідація кешу | `200 OK` | `400 Bad Request` (недійсний токен або користувача не знайдено) |

### 👤 Користувачі та профіль (`users`)

| Метод | Маршрут | Опис операції | Успішний статус | Очікувані помилки |
| :---: | :--- | :--- | :---: | :--- |
| **GET** | `/api/users/me` | Отримання профілю авторизованого користувача (Redis-кеш, ліміт: 10/хв) | `200 OK` | `401 Unauthorized`, `429 Too Many Requests` |
| **PATCH** | `/api/users/avatar` | Оновлення аватара в Cloudinary (доступно тільки для ролі `admin`) | `200 OK` | `401 Unauthorized`, `403 Forbidden` (для звичайних користувачів) |

### 👥 Контакти з суворою ізоляцією (`contacts`)

| Метод | Маршрут | Опис операції | Успішний статус | Очікувані помилки |
| :---: | :--- | :--- | :---: | :--- |
| **GET** | `/api/contacts/birthdays` | Список контактів із днями народження на найближчі N днів (дефолт: 7) | `200 OK` | `401 Unauthorized`, `422 Unprocessable` |
| **POST** | `/api/contacts` | Створити новий контакт у власній книзі | `201 Created` | `401 Unauthorized`, `409 Conflict` (дублікат email/телефону) |
| **GET** | `/api/contacts` | Отримати список власних контактів (фільтрація за іменем, email, пагінація) | `200 OK` | `401 Unauthorized` |
| **GET** | `/api/contacts/{id}` | Отримати контакт за ID (чужі контакти повертають 404) | `200 OK` | `401 Unauthorized`, `404 Not Found` |
| **PUT** | `/api/contacts/{id}` | Повне оновлення власного контакту | `200 OK` | `401 Unauthorized`, `404 Not Found`, `409 Conflict` |
| **PATCH** | `/api/contacts/{id}` | Часткове оновлення окремих полів контакту | `200 OK` | `401 Unauthorized`, `404 Not Found`, `409 Conflict` |
| **DELETE** | `/api/contacts/{id}` | Видалення контакту зі своєї книги | `204 No Content` | `401 Unauthorized`, `404 Not Found` |

### 🩺 Діагностика та стан системи (`ops`)

| Метод | Маршрут | Опис операції | Успішний статус | Помилка сервісу |
| :---: | :--- | :--- | :---: | :--- |
| **GET** | `/healthz` | Перевірка працездатності сервера та з'єднання з базою PostgreSQL | `200 OK` | `503 Service Unavailable` |

---

## ☁️ Розгортання у хмарі (Render)

Застосунок оптимізовано для безкоштовного хмарного розгортання на платформі **Render.com** за допомогою Docker-образу.

### Особливості та архітектурні рішення для хмари:
1. **Спільний регіон (Critical Rule):**  
   Для мінімізації мережевих затримок та стабільного з'єднання базу даних PostgreSQL та вебсервіс обов'язково створювати в одному регіоні — **`Frankfurt (EU Central)`**.
2. **Конфігурація PostgreSQL:**  
   Платформа Render забороняє використання імені `postgres` як користувача. Застосовано стандартне ім'я `admin` та назву БД `mydb`. Підключення вебсервісу виконується через швидкісне внутрішнє ім'я хоста (**Internal Database URL**).
3. **Підтримка динамічного порту (`$PORT`) та міграції:**  
   Скрипт запуску `entrypoint.sh` автоматично адаптується під динамічний порт платформи `${PORT:-8000}`, коректно передає системні сигнали (SIGTERM) та виконує міграції `uv run alembic upgrade head` перед стартом сервера.
4. **Робота без стороннього SMTP та стійкість до відсутності Redis:**  
   - Увімкнення `MAIL_SIMULATE=True` та `DEBUG_SHOW_TOKEN_IN_LOGS=True` дозволяє ментору протестувати роботу пошти прямо через Swagger UI та логи Render без підняття зовнішнього SMTP.
   - Механізм відмовостійкості (graceful fallback) у коді кешування дозволяє застосунку працювати стабільно навіть без окремого платного інстансу Redis у безкоштовному тарифі.

### Змінні оточення на Render (Environment Variables):

| Ключ (Key) | Орієнтовне значення (Value) | Призначення |
| :--- | :--- | :--- |
| `DB_HOST` | `dpg-xxxxxxxxxxxx-a` | Внутрішнє ім'я хоста (Internal Database Hostname) |
| `DB_PORT` | `5432` | Порт PostgreSQL |
| `DB_USER` | `admin` | Обраний користувач БД на Render |
| `DB_PASSWORD` | `ваш_пароль_бд` | Наданий пароль бази даних на Render |
| `DB_NAME` | `mydb` | Обрана вами назва БД на Render |
| `SECRET_KEY` | `довгий_рандомний_ключ_безпеки` | Секретний ключ криптографічного підпису JWT |
| `ALGORITHM` | `HS256` | Алгоритм підпису JWT |
| `REDIS_HOST` | `localhost` | Локальний хост (заглушка) або зовнішній Redis (Upstash) |
| `REDIS_PORT` | `6379` | Порт Redis |
| `MAIL_SIMULATE` | `True` | Локальна симуляція пошти для миттєвої активації (не працює в рамках Render) |
| `DEBUG_SHOW_TOKEN_IN_LOGS` | `True` | Виведення посилань верифікації у журнал логів Render |
| `CLOUDINARY_NAME` | `ваша_назва_хмари` | Це і нижче ваші параметри Cloudinary для тестування аватарів |
| `CLOUDINARY_API_KEY` | `ваш_api_key` | -- |
| `CLOUDINARY_API_SECRET` | `ваш_api_secret` | -- |

---

## 🔗 Офіційні посилання розгорнутого проєкту (Render)

- 🌐 **Публічний інтерактивний Swagger UI:** **[https://vb2026api.onrender.com/docs](https://vb2026api.onrender.com/docs)**
- 🩺 **Перевірка доступності сервісу (Health Check):** **[https://vb2026api.onrender.com/healthz](https://vb2026api.onrender.com/healthz)**

> **Примітка щодо «холодного старту»:**  
> На безкоштовному тарифі Render після періоду простою сервіс переходить у сплячий режим. Перше відкриття сторінки може тривати 30–50 секунд, після чого сервер працює у штатному високошвидкісному режимі.
