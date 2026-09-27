"""Модульні тести для UserRepository з використанням моків AsyncSession."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models import User
from src.repository import UserRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    """Фікстура замокованої асинхронної сесії SQLAlchemy."""
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def user_repo(mock_session: AsyncMock) -> UserRepository:
    """Фікстура репозиторію користувачів з моком сесії."""
    return UserRepository(mock_session)


@pytest.mark.asyncio
async def test_get_by_id_found(
    user_repo: UserRepository, mock_session: AsyncMock
) -> None:
    """Успішний пошук користувача за числовим ID."""
    mock_user = User(id=1, username="test", email="test@example.com")
    mock_session.scalar.return_value = mock_user

    result = await user_repo.get_by_id(1)

    assert result == mock_user
    mock_session.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_id_not_found(
    user_repo: UserRepository, mock_session: AsyncMock
) -> None:
    """Пошук користувача за неіснуючим ID повертає None."""
    mock_session.scalar.return_value = None

    result = await user_repo.get_by_id(999)

    assert result is None
    mock_session.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_email_found(
    user_repo: UserRepository, mock_session: AsyncMock
) -> None:
    """Успішний пошук користувача за email."""
    mock_user = User(id=1, username="test", email="test@example.com")
    mock_session.scalar.return_value = mock_user

    result = await user_repo.get_by_email("test@example.com")

    assert result == mock_user
    mock_session.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_email_not_found(
    user_repo: UserRepository, mock_session: AsyncMock
) -> None:
    """Пошук користувача за неіснуючим email повертає None."""
    mock_session.scalar.return_value = None

    result = await user_repo.get_by_email("missing@example.com")

    assert result is None
    mock_session.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_username_found(
    user_repo: UserRepository, mock_session: AsyncMock
) -> None:
    """Успішний пошук користувача за username."""
    mock_user = User(id=1, username="john", email="john@example.com")
    mock_session.scalar.return_value = mock_user

    result = await user_repo.get_by_username("john")

    assert result == mock_user
    mock_session.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_username_not_found(
    user_repo: UserRepository, mock_session: AsyncMock
) -> None:
    """Пошук користувача за неіснуючим username повертає None."""
    mock_session.scalar.return_value = None

    result = await user_repo.get_by_username("ghost")

    assert result is None
    mock_session.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_user(user_repo: UserRepository, mock_session: AsyncMock) -> None:
    """Створення нового користувача з викликом add, flush та refresh."""
    user = await user_repo.create("newuser", "new@example.com", "secret_hash")

    assert user.username == "newuser"
    assert user.email == "new@example.com"
    assert user.hashed_password == "secret_hash"
    mock_session.add.assert_called_once_with(user)
    mock_session.flush.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(user)


@pytest.mark.asyncio
async def test_confirm_email_success(
    user_repo: UserRepository, mock_session: AsyncMock
) -> None:
    """Успішна верифікація пошти знайденого користувача."""
    mock_user = User(id=1, email="test@example.com", confirmed=False)
    mock_session.scalar.return_value = mock_user

    await user_repo.confirm_email("test@example.com")

    assert mock_user.confirmed is True
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirm_email_user_not_found(
    user_repo: UserRepository, mock_session: AsyncMock
) -> None:
    """Спроба підтвердження пошти для неіснуючого користувача не викликає flush."""
    mock_session.scalar.return_value = None

    await user_repo.confirm_email("missing@example.com")

    mock_session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_update_avatar_success(
    user_repo: UserRepository, mock_session: AsyncMock
) -> None:
    """Успішне оновлення URL аватара користувача."""
    mock_user = User(id=1, email="test@example.com", avatar_url=None)
    mock_session.scalar.return_value = mock_user

    result = await user_repo.update_avatar(
        "test@example.com", "https://avatar.url/pic.jpg"
    )

    assert result.avatar_url == "https://avatar.url/pic.jpg"
    mock_session.flush.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(mock_user)


@pytest.mark.asyncio
async def test_update_avatar_not_found_raises(
    user_repo: UserRepository, mock_session: AsyncMock
) -> None:
    """Спроба оновлення аватара неіснуючого користувача викликає ValueError."""
    mock_session.scalar.return_value = None

    with pytest.raises(ValueError, match="не знайдено"):
        await user_repo.update_avatar(
            "missing@example.com", "https://avatar.url/pic.jpg"
        )


@pytest.mark.asyncio
async def test_update_password_success(
    user_repo: UserRepository, mock_session: AsyncMock
) -> None:
    """Успішне оновлення хешованого пароля користувача."""
    mock_user = User(id=1, email="test@example.com", hashed_password="old_hash")
    mock_session.scalar.return_value = mock_user

    result = await user_repo.update_password("test@example.com", "new_hash")

    assert result.hashed_password == "new_hash"
    mock_session.flush.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(mock_user)


@pytest.mark.asyncio
async def test_update_password_not_found_raises(
    user_repo: UserRepository, mock_session: AsyncMock
) -> None:
    """Спроба оновлення пароля неіснуючого користувача викликає ValueError."""
    mock_session.scalar.return_value = None

    with pytest.raises(ValueError, match="не знайдено"):
        await user_repo.update_password("missing@example.com", "new_hash")
