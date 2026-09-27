"""Асинхронний рушій БД та генератор сесій для транзакцій."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .settings import settings

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

# expire_on_commit=False обов'язковий в асинхронному режимі,
# щоб читання полів після commit() не викликало lazy load помилку MissingGreenlet
SessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    class_=AsyncSession,
)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    """Контекстний менеджер однієї транзакції для зовнішніх скриптів, тестів та утиліт.

    Автоматично фіксує (commit) зміни у разі успішного виконання або
    виконує відкат (rollback) при виникненні будь-якого винятку, після чого закриває сесію.

    Yields:
        AsyncSession: Активна асинхронна сесія SQLAlchemy.

    Raises:
        Exception: Будь-який виняток, що виник під час виконання операцій у блоці with.
    """
    session = SessionLocal()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db() -> AsyncIterator[AsyncSession]:
    """Генератор залежності FastAPI для отримання сесії бази даних.

    Створює ізольовану сесію та транзакцію на час обробки одного HTTP-запиту.
    Сесія автоматично закривається після формування відповіді.

    Yields:
        AsyncSession: Асинхронна сесія для використання в ендпоінтах.
    """
    async with get_session() as session:
        yield session
