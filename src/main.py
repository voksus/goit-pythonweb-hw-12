"""Головний модуль FastAPI застосунку з CORS, SlowAPI та роутерами."""

# Запобігання `psycopg.InterfaceError`.
# Під Win за замовчуванням ProactorEventLoop в `asyncio`,
# а `psycopg 3` вимагає SelectorEventLoop
import sys
from contextlib import asynccontextmanager

if sys.platform == "win32":
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .dependencies import SessionDep
from .repository import ContactRepository
from .routers import auth, contacts, users
from .routers.users import limiter
from .schemas import HealthCheck
from .services.cache import close_redis_client, get_redis_client
from .settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Керування життєвим циклом застосунку (Lifespan).

    Виконує перевірку з'єднання з Redis під час старту застосунку
    та гарантує коректне закриття пулу з'єднань Redis при його зупинці.

    Args:
        app: Екземпляр головного FastAPI застосунку.

    Yields:
        None: Передає керування на час активної роботи сервера.
    """
    redis = get_redis_client()
    try:
        await redis.ping()
    except Exception:
        pass
    yield
    await close_redis_client()


app = FastAPI(
    title=settings.app_title,
    description=settings.app_description,
    version=settings.app_version,
    lifespan=lifespan,
)

# 1. Підключення CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 2. Підключення SlowAPI Rate Limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 3. Підключення роутерів
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(contacts.router)


@app.get(
    "/healthz",
    response_model=HealthCheck,
    tags=["ops"],
    summary="Перевірка доступності сервісу та бази даних",
)
async def health_check(session: SessionDep, response: Response) -> HealthCheck:
    """Перевірка стану працездатності сервісу та підключення до бази даних.

    Виконує тестовий SQL-пінг до БД. Якщо база недоступна, статус відповіді
    змінюється на 503 Service Unavailable.

    Args:
        session: Асинхронна сесія бази даних (впроваджена залежність).
        response: Об'єкт відповіді FastAPI для встановлення HTTP-статусу.

    Returns:
        HealthCheck: Схема зі статусами працездатності застосунку та БД.
    """
    is_db_ok = await ContactRepository(session).ping()
    if not is_db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthCheck(
        status="ok" if is_db_ok else "error",
        database="ok" if is_db_ok else "unreachable",
    )
