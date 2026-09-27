"""Модульні тести для ContactRepository з використанням моків AsyncSession."""

from datetime import date, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models import Contact, User
from src.repository import ContactRepository
from src.schemas import ContactCreate


@pytest.fixture
def mock_session() -> AsyncMock:
    """Фікстура замокованої асинхронної сесії SQLAlchemy."""
    session = AsyncMock()
    session.add = MagicMock()
    return session


@pytest.fixture
def contact_repo(mock_session: AsyncMock) -> ContactRepository:
    """Фікстура репозиторію контактів з моком сесії."""
    return ContactRepository(mock_session)


@pytest.fixture
def test_user() -> User:
    """Тестовий об'єкт користувача-власника."""
    return User(id=1, username="john", email="john@example.com")


@pytest.mark.asyncio
async def test_ping_success(
    contact_repo: ContactRepository, mock_session: AsyncMock
) -> None:
    """Перевірка ping повертає True при успішній відповіді бази 1."""
    mock_session.scalar.return_value = 1

    assert await contact_repo.ping() is True


@pytest.mark.asyncio
async def test_ping_failure(
    contact_repo: ContactRepository, mock_session: AsyncMock
) -> None:
    """Перевірка ping повертає False при виникненні будь-якого винятку."""
    mock_session.scalar.side_effect = Exception("DB Connection Error")

    assert await contact_repo.ping() is False


@pytest.mark.asyncio
async def test_get_by_id_found(
    contact_repo: ContactRepository, mock_session: AsyncMock, test_user: User
) -> None:
    """Успішне отримання контакту за ID з перевіркою власника."""
    mock_contact = Contact(id=1, first_name="Alice", user_id=test_user.id)
    mock_session.scalar.return_value = mock_contact

    result = await contact_repo.get_by_id(1, test_user)

    assert result == mock_contact
    mock_session.scalar.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_by_id_not_found(
    contact_repo: ContactRepository, mock_session: AsyncMock, test_user: User
) -> None:
    """Пошук неіснуючого контакту за ID повертає None."""
    mock_session.scalar.return_value = None

    result = await contact_repo.get_by_id(999, test_user)

    assert result is None


@pytest.mark.asyncio
async def test_get_by_email_found(
    contact_repo: ContactRepository, mock_session: AsyncMock, test_user: User
) -> None:
    """Успішний пошук контакту за email серед контактів користувача."""
    mock_contact = Contact(id=1, email="alice@example.com", user_id=test_user.id)
    mock_session.scalar.return_value = mock_contact

    result = await contact_repo.get_by_email("alice@example.com", test_user)

    assert result == mock_contact


@pytest.mark.asyncio
async def test_get_by_phone_found(
    contact_repo: ContactRepository, mock_session: AsyncMock, test_user: User
) -> None:
    """Успішний пошук контакту за номером телефону."""
    mock_contact = Contact(id=1, phone_number="+380501234567", user_id=test_user.id)
    mock_session.scalar.return_value = mock_contact

    result = await contact_repo.get_by_phone("+380501234567", test_user)

    assert result == mock_contact


@pytest.mark.asyncio
async def test_list_contacts_basic(
    contact_repo: ContactRepository, mock_session: AsyncMock, test_user: User
) -> None:
    """Отримання списку контактів без додаткових фільтрів."""
    mock_contacts = [
        Contact(id=1, first_name="A", user_id=test_user.id),
        Contact(id=2, first_name="B", user_id=test_user.id),
    ]
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = mock_contacts
    mock_session.scalars.return_value = mock_scalars

    result = await contact_repo.list_contacts(user=test_user, skip=0, limit=10)

    assert len(result) == 2
    assert result == mock_contacts


@pytest.mark.asyncio
async def test_list_contacts_with_filters(
    contact_repo: ContactRepository, mock_session: AsyncMock, test_user: User
) -> None:
    """Отримання списку контактів з усіма типами фільтрації."""
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_session.scalars.return_value = mock_scalars

    result = await contact_repo.list_contacts(
        user=test_user,
        search="Alice",
        first_name="Ali",
        last_name="Smith",
        email="alice@test.com",
    )

    assert result == []
    mock_session.scalars.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_contact(
    contact_repo: ContactRepository, mock_session: AsyncMock, test_user: User
) -> None:
    """Створення контакту з викликом add, flush та refresh."""
    body = ContactCreate(
        first_name="Jane",
        last_name="Doe",
        email="jane@example.com",
        phone_number="+380991112233",
        birthday=date(1995, 5, 20),
        extra_data="Friend",
    )

    contact = await contact_repo.create(body, test_user)

    assert contact.first_name == "Jane"
    assert contact.user_id == test_user.id
    mock_session.add.assert_called_once_with(contact)
    mock_session.flush.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(contact)


@pytest.mark.asyncio
async def test_update_contact(
    contact_repo: ContactRepository, mock_session: AsyncMock
) -> None:
    """Оновлення полів наявного контакту."""
    contact = Contact(id=1, first_name="OldName", last_name="OldLast")

    updated = await contact_repo.update(contact, {"first_name": "NewName"})

    assert updated.first_name == "NewName"
    assert updated.last_name == "OldLast"
    mock_session.flush.assert_awaited_once()
    mock_session.refresh.assert_awaited_once_with(contact)


@pytest.mark.asyncio
async def test_delete_contact(
    contact_repo: ContactRepository, mock_session: AsyncMock
) -> None:
    """Видалення контакту з бази даних."""
    contact = Contact(id=1, first_name="ToDelete")

    await contact_repo.delete(contact)

    mock_session.delete.assert_awaited_once_with(contact)
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_upcoming_birthdays_logic(
    contact_repo: ContactRepository, mock_session: AsyncMock, test_user: User
) -> None:
    """Перевірка бізнес-логіки визначення найближчих днів народження."""
    today = date.today()

    # 1. День народження через 3 дні (має увійти у 7 днів)
    target_upcoming = today + timedelta(days=3)
    c_upcoming = Contact(
        id=1,
        first_name="Upcoming",
        birthday=target_upcoming.replace(year=target_upcoming.year - 20),
        user_id=test_user.id,
    )
    # 2. День народження вчора (минув у цьому році)
    target_past = today - timedelta(days=2)
    c_past = Contact(
        id=2,
        first_name="Past",
        birthday=target_past.replace(year=target_past.year - 25),
        user_id=test_user.id,
    )
    # 3. Високосний день народження 29 лютого
    c_leap = Contact(
        id=3,
        first_name="Leap",
        birthday=date(2000, 2, 29),
        user_id=test_user.id,
    )

    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [c_upcoming, c_past, c_leap]
    mock_session.scalars.return_value = mock_scalars

    result = await contact_repo.get_upcoming_birthdays(user=test_user, days=7)

    assert c_upcoming in result
    assert c_past not in result
