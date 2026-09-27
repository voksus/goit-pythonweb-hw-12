"""Інтеграційні тести маршрутів автентифікації: реєстрація, логін, токени, верифікація та скидання пароля."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User
from src.services.security import auth_service
from tests.conftest import FakeRedis


@pytest.mark.asyncio
async def test_register_user_success(
    client: AsyncClient, db_session: AsyncSession
) -> None:
    """Успішна реєстрація нового користувача зі статусом 201 Created."""
    payload = {
        "username": "newbie",
        "email": "newbie@example.com",
        "password": "Password123!",
    }
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newbie"
    assert data["email"] == "newbie@example.com"
    assert data["role"] == "user"
    assert data["confirmed"] is False
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_email(
    client: AsyncClient, confirmed_user: User
) -> None:
    """Спроба реєстрації з наявним email повертає 409 Conflict."""
    payload = {
        "username": "unique_username",
        "email": confirmed_user.email,
        "password": "Password123!",
    }
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 409
    assert "електронної пошти вже зареєстрований" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_duplicate_username(
    client: AsyncClient, confirmed_user: User
) -> None:
    """Спроба реєстрації з наявним username повертає 409 Conflict."""
    payload = {
        "username": confirmed_user.username,
        "email": "unique_email@example.com",
        "password": "Password123!",
    }
    response = await client.post("/api/auth/register", json=payload)

    assert response.status_code == 409
    assert "іменем вже існує" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_success_and_caches_user(
    client: AsyncClient,
    confirmed_user: User,
    user_data: dict[str, str],
    fake_redis: FakeRedis,
) -> None:
    """Успішний логін повертає пару токенів та зберігає сутність у кеш Redis."""
    form_data = {
        "username": confirmed_user.email,
        "password": user_data["password"],
    }
    response = await client.post("/api/auth/login", data=form_data)

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"

    # Перевірка наявності користувача в Redis-кеші
    cached_raw = await fake_redis.get(f"user:{confirmed_user.email}")
    assert cached_raw is not None
    assert confirmed_user.email in cached_raw


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, confirmed_user: User) -> None:
    """Вхід з невірним паролем повертає 401 Unauthorized."""
    form_data = {
        "username": confirmed_user.email,
        "password": "WrongPassword!",
    }
    response = await client.post("/api/auth/login", data=form_data)

    assert response.status_code == 401
    assert "Невірний логін або пароль" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_unconfirmed_email(
    client: AsyncClient, db_session: AsyncSession, user_data: dict[str, str]
) -> None:
    """Спроба входу непідтвердженого користувача повертає 401 Unauthorized."""
    hashed = await auth_service.hash_password(user_data["password"])
    unconfirmed = User(
        username="unconfirmed_user",
        email="unconf@example.com",
        hashed_password=hashed,
        confirmed=False,
    )
    db_session.add(unconfirmed)
    await db_session.commit()

    form_data = {
        "username": unconfirmed.email,
        "password": user_data["password"],
    }
    response = await client.post("/api/auth/login", data=form_data)

    assert response.status_code == 401
    assert "Електронна пошта не підтверджена" in response.json()["detail"]


@pytest.mark.asyncio
async def test_refresh_token_success(client: AsyncClient, confirmed_user: User) -> None:
    """Оновлення пари access та refresh токенів за валідним refresh токеном."""
    refresh_token = await auth_service.create_refresh_token(confirmed_user.email)
    response = await client.post(
        "/api/auth/refresh_token", json={"refresh_token": refresh_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_token_invalid(client: AsyncClient) -> None:
    """Спроба оновлення за недійсним refresh токеном повертає 401."""
    response = await client.post(
        "/api/auth/refresh_token", json={"refresh_token": "bad_token"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_confirmed_email_flow(
    client: AsyncClient, db_session: AsyncSession, user_data: dict[str, str]
) -> None:
    """Повний флоу підтвердження адреси електронної пошти за одноразовим токеном."""
    hashed = await auth_service.hash_password(user_data["password"])
    user = User(
        username="to_confirm",
        email="to_confirm@example.com",
        hashed_password=hashed,
        confirmed=False,
    )
    db_session.add(user)
    await db_session.commit()

    token = await auth_service.create_verification_token(user.email)
    response = await client.get(f"/api/auth/confirmed_email/{token}")

    assert response.status_code == 200
    assert "успішно підтверджено" in response.json()["message"]

    # Повторний перехід за тим самим посиланням
    second_response = await client.get(f"/api/auth/confirmed_email/{token}")
    assert second_response.status_code == 200
    assert "вже була підтверджена" in second_response.json()["message"]


@pytest.mark.asyncio
async def test_request_email_endpoint(
    client: AsyncClient, confirmed_user: User
) -> None:
    """Запит повторної відправки листа верифікації повертає стандартизоване повідомлення."""
    response = await client.post(
        "/api/auth/request_email", json={"email": confirmed_user.email}
    )
    assert response.status_code == 200
    assert "лист для активації відправлено" in response.json()["message"]


@pytest.mark.asyncio
async def test_forgot_password_and_reset_password_flow(
    client: AsyncClient, confirmed_user: User, db_session: AsyncSession
) -> None:
    """Повний флоу скидання пароля: запит токена, оновлення пароля та успішний вхід."""
    # 1. Запит на скидання
    forgot_res = await client.post(
        "/api/auth/forgot-password", json={"email": confirmed_user.email}
    )
    assert forgot_res.status_code == 200
    assert "інструкціями для скидання" in forgot_res.json()["message"]

    # 2. Формування валідного токена скидання
    reset_token = await auth_service.create_password_reset_token(confirmed_user.email)

    # 3. Встановлення нового пароля
    new_password = "BrandNewPassword2026!"
    reset_res = await client.post(
        "/api/auth/reset-password",
        json={"token": reset_token, "new_password": new_password},
    )
    assert reset_res.status_code == 200
    assert "Пароль успішно змінено" in reset_res.json()["message"]

    # 4. Перевірка входу з новим паролем
    login_res = await client.post(
        "/api/auth/login",
        data={"username": confirmed_user.email, "password": new_password},
    )
    assert login_res.status_code == 200
    assert "access_token" in login_res.json()


@pytest.mark.asyncio
async def test_reset_password_invalid_token(client: AsyncClient) -> None:
    """Спроба скидання пароля з недійсним токеном повертає 400 Bad Request."""
    response = await client.post(
        "/api/auth/reset-password",
        json={"token": "corrupted_token", "new_password": "NewPassword123!"},
    )
    assert response.status_code == 400
