"""Конфігурація тестового середовища: SQLite in-memory, FakeRedis, клієнти та фікстури."""

from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from src.db import get_db
from src.dependencies import get_redis_client
from src.main import app
from src.models import Base, User, UserRole
from src.services.cache import cache_service
from src.services.security import auth_service
from src.services.upload_file import UploadFileService
from src.settings import settings


class FakeRedis:
    """Швидка in-memory імітація Redis для автономних модульних та інтеграційних тестів.

    Зберігає ключі у звичайному Python-словнику, підтримує базові команди get, set, delete,
    ping та close. Це усуває потребу у піднятті реального Redis під час локального тестування.
    """

    def __init__(self) -> None:
        self._store: dict[str, str] = {}

    async def get(self, name: str) -> str | None:
        return self._store.get(name)

    async def set(self, name: str, value: str, ex: int | None = None) -> bool:
        self._store[name] = str(value)
        return True

    async def delete(self, *names: str) -> int:
        count = 0
        for name in names:
            if name in self._store:
                del self._store[name]
                count += 1
        return count

    async def ping(self) -> bool:
        return True

    async def close(self) -> None:
        pass

    def clear(self) -> None:
        self._store.clear()


@pytest.fixture
def fake_redis() -> FakeRedis:
    """Фікстура екземпляра FakeRedis."""
    return FakeRedis()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncIterator[AsyncSession]:
    """Ізольована сесія SQLite in-memory з пулом StaticPool для кожного тесту.

    StaticPool підтримує єдине з'єднання для in-memory бази на час тесту,
    що дозволяє зберігати створені таблиці між запитами без видалення з пам'яті.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def client(
    db_session: AsyncSession, fake_redis: FakeRedis, monkeypatch: pytest.MonkeyPatch
) -> AsyncIterator[AsyncClient]:
    """Асинхронний HTTP-клієнт httpx для тестування API маршрутів FastAPI.

    Перевизначає залежності get_db та get_redis_client, вимикає rate limiter
    та мокує зовнішні сервіси (пошта, хмарне сховище Cloudinary).
    """

    async def override_get_db() -> AsyncIterator[AsyncSession]:
        try:
            yield db_session
            await db_session.commit()
        except Exception:
            await db_session.rollback()
            raise

    # 1. Підміна залежностей FastAPI
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_redis_client] = lambda: fake_redis
    cache_service._client = fake_redis

    # 2. Вимкнення лімітера SlowAPI на час тестів (запобігання помилкам 429 Too Many Requests)
    app.state.limiter.enabled = False

    # 3. Мокування відправки пошти (вмикаємо симуляцію)
    monkeypatch.setattr(settings, "mail_simulate", True)

    # 4. Мокування завантаження аватара в Cloudinary
    monkeypatch.setattr(
        UploadFileService,
        "upload_file",
        lambda self, file, username: (
            f"https://res.cloudinary.com/test/image/upload/v12345/RestApp/{username}.jpg"
        ),
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    # Очищення стану після тесту
    app.dependency_overrides.clear()
    cache_service._client = None
    app.state.limiter.enabled = True
    fake_redis.clear()


@pytest.fixture
def user_data() -> dict[str, str]:
    """Тестові дані для створення стандартного користувача."""
    return {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "Password123!",
    }


@pytest.fixture
def admin_data() -> dict[str, str]:
    """Тестові дані для створення адміністратора."""
    return {
        "username": "adminuser",
        "email": "admin@example.com",
        "password": "AdminPassword123!",
    }


@pytest_asyncio.fixture
async def confirmed_user(db_session: AsyncSession, user_data: dict[str, str]) -> User:
    """Фікстура підтвердженого користувача з базовою роллю 'user'."""
    hashed = await auth_service.hash_password(user_data["password"])
    user = User(
        username=user_data["username"],
        email=user_data["email"],
        hashed_password=hashed,
        role=UserRole.USER,
        confirmed=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def confirmed_admin(db_session: AsyncSession, admin_data: dict[str, str]) -> User:
    """Фікстура підтвердженого адміністратора з роллю 'admin'."""
    hashed = await auth_service.hash_password(admin_data["password"])
    admin = User(
        username=admin_data["username"],
        email=admin_data["email"],
        hashed_password=hashed,
        role=UserRole.ADMIN,
        confirmed=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def user_token_headers(confirmed_user: User) -> dict[str, str]:
    """Заголовок авторизації Bearer токена для звичайного користувача."""
    token = await auth_service.create_access_token(confirmed_user.email)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def admin_token_headers(confirmed_admin: User) -> dict[str, str]:
    """Заголовок авторизації Bearer токена для адміністратора."""
    token = await auth_service.create_access_token(confirmed_admin.email)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def second_user(db_session: AsyncSession) -> User:
    """Другий ізольований користувач для перевірки розмежування доступу до контактів."""
    hashed = await auth_service.hash_password("SecondPassword123!")
    user = User(
        username="seconduser",
        email="second@example.com",
        hashed_password=hashed,
        role=UserRole.USER,
        confirmed=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def second_user_token_headers(second_user: User) -> dict[str, str]:
    """Заголовок авторизації Bearer токена для другого користувача."""
    token = await auth_service.create_access_token(second_user.email)
    return {"Authorization": f"Bearer {token}"}
