"""Інтеграційні тести профілю користувача (/me) та перевірки прав ролей на аватар (RBAC)."""

import io

import pytest
from httpx import AsyncClient

from src.models import User
from tests.conftest import FakeRedis


@pytest.mark.asyncio
async def test_get_me_success(
    client: AsyncClient,
    confirmed_user: User,
    user_token_headers: dict[str, str],
) -> None:
    """Отримання власного профілю поточного автентифікованого користувача."""
    response = await client.get("/api/users/me", headers=user_token_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == confirmed_user.email
    assert data["username"] == confirmed_user.username
    assert data["role"] == "user"


@pytest.mark.asyncio
async def test_get_me_uses_redis_cache(
    client: AsyncClient,
    confirmed_user: User,
    user_token_headers: dict[str, str],
    fake_redis: FakeRedis,
) -> None:
    """Повторний запит /me зчитує дані з кешу Redis без звернення до БД."""
    # 1. Перший запит кешує користувача
    res1 = await client.get("/api/users/me", headers=user_token_headers)
    assert res1.status_code == 200

    # Перевіряємо, що ключ з'явився в кеші
    cached_data = await fake_redis.get(f"user:{confirmed_user.email}")
    assert cached_data is not None

    # 2. Другий запит повертає ті самі дані з кешу
    res2 = await client.get("/api/users/me", headers=user_token_headers)
    assert res2.status_code == 200
    assert res2.json()["email"] == confirmed_user.email


@pytest.mark.asyncio
async def test_get_me_unauthorized(client: AsyncClient) -> None:
    """Звернення до /me без авторизаційного токена повертає 401 Unauthorized."""
    response = await client.get("/api/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_avatar_upload_forbidden_for_regular_user(
    client: AsyncClient, user_token_headers: dict[str, str]
) -> None:
    """Звичайний користувач (role=user) отримує 403 Forbidden при спробі оновити аватар."""
    file_content = b"fake_image_bytes"
    files = {"file": ("avatar.png", io.BytesIO(file_content), "image/png")}

    response = await client.patch(
        "/api/users/avatar", headers=user_token_headers, files=files
    )

    assert response.status_code == 403
    assert "дозволена лише адміністраторам" in response.json()["detail"]


@pytest.mark.asyncio
async def test_avatar_upload_success_for_admin(
    client: AsyncClient,
    confirmed_admin: User,
    admin_token_headers: dict[str, str],
    fake_redis: FakeRedis,
) -> None:
    """Адміністратор (role=admin) успішно змінює аватар, і старий кеш інвалідується."""
    # Попередньо поміщаємо адміна в кеш
    await fake_redis.set(f"user:{confirmed_admin.email}", "cached_admin_data")

    file_content = b"fake_admin_avatar_bytes"
    files = {"file": ("admin_avatar.png", io.BytesIO(file_content), "image/png")}

    response = await client.patch(
        "/api/users/avatar", headers=admin_token_headers, files=files
    )

    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "admin"
    assert "avatar_url" in data
    assert "cloudinary.com" in data["avatar_url"]

    # Перевірка інвалідації кешу Redis
    cache_after = await fake_redis.get(f"user:{confirmed_admin.email}")
    assert cache_after is None


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient) -> None:
    """Ендпоінт /healthz повертає статус ok для сервісу та бази даних."""
    response = await client.get("/healthz")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"
