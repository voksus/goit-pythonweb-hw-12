"""Модульні тести для AuthService: паролі, JWT токени та перевірка помилок валідації."""

import pytest
from fastapi import HTTPException
from jose import jwt

from src.services.security import auth_service
from src.settings import settings


@pytest.mark.asyncio
async def test_password_hash_and_verify() -> None:
    """Перевірка коректності хешування та верифікації пароля за допомогою bcrypt."""
    plain = "MySecretPassword123!"
    hashed = await auth_service.hash_password(plain)

    assert hashed != plain
    assert await auth_service.verify_password(plain, hashed) is True
    assert await auth_service.verify_password("WrongPassword!", hashed) is False


@pytest.mark.asyncio
async def test_access_token_creation_and_payload() -> None:
    """Перевірка структури та полів згенерованого access-токена."""
    email = "user@example.com"
    token = await auth_service.create_access_token(email)

    payload = jwt.decode(
        token,
        settings.secret_key.get_secret_value(),
        algorithms=[auth_service.ALGORITHM],
    )
    assert payload["sub"] == email
    assert payload["scope"] == "access_token"
    assert "exp" in payload


@pytest.mark.asyncio
async def test_refresh_token_lifecycle() -> None:
    """Успішне створення та декодування refresh токена."""
    email = "refresh@example.com"
    token = await auth_service.create_refresh_token(email)

    decoded_email = await auth_service.decode_refresh_token(token)
    assert decoded_email == email


@pytest.mark.asyncio
async def test_decode_refresh_token_invalid_raises() -> None:
    """Спроба декодувати пошкоджений refresh токен підіймає 401 HTTPException."""
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.decode_refresh_token("invalid.token.string")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_decode_refresh_token_wrong_scope_raises() -> None:
    """Передача access-токена у метод декодування refresh-токена викликає 401."""
    access_token = await auth_service.create_access_token("test@example.com")
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.decode_refresh_token(access_token)
    assert exc_info.value.status_code == 401
    assert "Недійсний тип" in exc_info.value.detail


@pytest.mark.asyncio
async def test_verification_token_lifecycle() -> None:
    """Успішне створення та декодування токена підтвердження пошти."""
    email = "verify@example.com"
    token = await auth_service.create_verification_token(email)

    decoded_email = await auth_service.decode_verification_token(token)
    assert decoded_email == email


@pytest.mark.asyncio
async def test_decode_verification_token_invalid_raises() -> None:
    """Спроба декодування невалідного токена верифікації викликає 422 HTTPException."""
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.decode_verification_token("corrupted_token")
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_password_reset_token_lifecycle() -> None:
    """Успішне створення та декодування токена скидання пароля."""
    email = "reset@example.com"
    token = await auth_service.create_password_reset_token(email)

    decoded_email = await auth_service.decode_password_reset_token(token)
    assert decoded_email == email


@pytest.mark.asyncio
async def test_decode_password_reset_token_wrong_scope_raises() -> None:
    """Токен з іншим scope під час скидання пароля викликає 400 HTTPException."""
    access_token = await auth_service.create_access_token("test@example.com")
    with pytest.raises(HTTPException) as exc_info:
        await auth_service.decode_password_reset_token(access_token)
    assert exc_info.value.status_code == 400
