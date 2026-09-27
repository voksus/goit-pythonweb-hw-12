"""Роутер контактів: повний набір REST CRUD операцій та пошуку з ізоляцією за користувачем."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Path, Query, status

from ..dependencies import CurrentUser, SessionDep
from ..models import Contact
from ..repository import ContactRepository
from ..schemas import ContactCreate, ContactResponse, ContactUpdate

router = APIRouter(prefix="/api/contacts", tags=["contacts"])

ContactId = Path(..., ge=1, description="Унікальний числовий ідентифікатор контакту")


async def _get_contact_or_404(
    repo: ContactRepository, contact_id: int, current_user: CurrentUser
) -> Contact:
    """Допоміжна функція для отримання контакту або підняття HTTP 404 Not Found.

    Args:
        repo: Екземпляр репозиторію контактів.
        contact_id: Ідентифікатор контакту.
        current_user: Поточний автентифікований користувач.

    Raises:
        HTTPException: 404 Not Found, якщо контакт не існує або належить іншому юзеру.

    Returns:
        Contact: Знайдений об'єкт контакту.
    """
    contact = await repo.get_by_id(contact_id, current_user)
    if contact is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Контакт з id {contact_id} не знайдено",
        )
    return contact


# -------------------------------------------------------------------------
# ВАЖЛИВО: /birthdays має бути оголошено ДО /{contact_id},
# щоб FastAPI не сприймав рядок 'birthdays' як числовий contact_id!
# -------------------------------------------------------------------------
@router.get(
    "/birthdays",
    response_model=list[ContactResponse],
    summary="Контакти з днями народження на найближчі 7 днів",
    description="Повертає список контактів поточного користувача, день народження яких настає у найближчі 7 днів.",
)
async def get_upcoming_birthdays(
    current_user: CurrentUser,
    session: SessionDep,
    days: int = Query(default=7, ge=1, le=365, description="Кількість днів уперед"),
) -> list[ContactResponse]:
    """Отримання списку контактів, чий день народження припадає на найближчі дні.

    Args:
        current_user: Поточний автентифікований користувач.
        session: Асинхронна сесія бази даних.
        days: Кількість днів для пошуку вперед (від 1 до 365, за замовчуванням 7).

    Returns:
        list[ContactResponse]: Список контактів із найближчими днями народження.
    """
    repo = ContactRepository(session)
    contacts = await repo.get_upcoming_birthdays(user=current_user, days=days)
    return [ContactResponse.model_validate(c) for c in contacts]


@router.post(
    "",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Email або номер телефону вже зареєстровані"},
    },
    summary="Створити новий контакт",
)
async def create_contact(
    body: ContactCreate,
    current_user: CurrentUser,
    session: SessionDep,
) -> ContactResponse:
    """Створення нового контакту для поточного користувача.

    Перевіряє унікальність електронної пошти та номера телефону серед контактів користувача.

    Args:
        body: Схема даних нового контакту.
        current_user: Поточний автентифікований користувач-власник.
        session: Асинхронна сесія бази даних.

    Raises:
        HTTPException: 409 Conflict, якщо email або номер телефону вже існують у контактах.

    Returns:
        ContactResponse: Створений контакт.
    """
    repo = ContactRepository(session)

    if await repo.get_by_email(body.email, current_user) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Контакт із поштою '{body.email}' вже існує",
        )
    if await repo.get_by_phone(body.phone_number, current_user) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Контакт із номером '{body.phone_number}' вже існує",
        )

    contact = await repo.create(body, current_user)
    return ContactResponse.model_validate(contact)


@router.get(
    "",
    response_model=list[ContactResponse],
    summary="Отримати список всіх контактів з можливістю пошуку",
)
async def list_contacts(
    current_user: CurrentUser,
    session: SessionDep,
    skip: int = Query(default=0, ge=0, description="Кількість контактів для пропуску"),
    limit: int = Query(
        default=100, ge=1, le=500, description="Максимум контактів у відповіді"
    ),
    search: str | None = Query(
        default=None,
        description="Загальний пошук за ім'ям, прізвищем чи email",
    ),
    first_name: str | None = Query(default=None, description="Фільтр за ім'ям"),
    last_name: str | None = Query(default=None, description="Фільтр за прізвищем"),
    email: str | None = Query(default=None, description="Фільтр за email"),
) -> list[ContactResponse]:
    """Отримання списку контактів поточного користувача з пагінацією та пошуком.

    Args:
        current_user: Поточний автентифікований користувач.
        session: Асинхронна сесія бази даних.
        skip: Кількість елементів для пропуску.
        limit: Максимальна кількість елементів.
        search: Рядок для загального пошуку (ім'я, прізвище або email).
        first_name: Фільтрація за точним/частковим ім'ям.
        last_name: Фільтрація за прізвищем.
        email: Фільтрація за email.

    Returns:
        list[ContactResponse]: Список знайдених контактів.
    """
    repo = ContactRepository(session)
    contacts = await repo.list_contacts(
        user=current_user,
        skip=skip,
        limit=limit,
        search=search,
        first_name=first_name,
        last_name=last_name,
        email=email,
    )
    return [ContactResponse.model_validate(c) for c in contacts]


@router.get(
    "/{contact_id}",
    response_model=ContactResponse,
    responses={404: {"description": "Контакт не знайдено"}},
    summary="Отримати один контакт за ідентифікатором",
)
async def get_contact(
    current_user: CurrentUser,
    session: SessionDep,
    contact_id: int = ContactId,
) -> ContactResponse:
    """Отримання детальної інформації про конкретний контакт за його ID.

    Args:
        current_user: Поточний автентифікований користувач.
        session: Асинхронна сесія бази даних.
        contact_id: Числовий ідентифікатор контакту.

    Returns:
        ContactResponse: Дані запитаного контакту.
    """
    repo = ContactRepository(session)
    contact = await _get_contact_or_404(repo, contact_id, current_user)
    return ContactResponse.model_validate(contact)


@router.put(
    "/{contact_id}",
    response_model=ContactResponse,
    responses={
        404: {"description": "Контакт не знайдено"},
        409: {"description": "Email або номер зайняті іншим контактом"},
    },
    summary="Повне оновлення існуючого контакту",
)
async def update_contact_full(
    body: ContactCreate,
    current_user: CurrentUser,
    session: SessionDep,
    contact_id: int = ContactId,
) -> ContactResponse:
    """Повне оновлення всіх полів контакту (PUT).

    Args:
        body: Нові значення для всіх обов'язкових полів контакту.
        current_user: Поточний користувач-власник.
        session: Асинхронна сесія бази даних.
        contact_id: Числовий ідентифікатор контакту.

    Raises:
        HTTPException: 404 Not Found, якщо контакт відсутній.
        HTTPException: 409 Conflict, якщо нова пошта або номер зайняті іншим контактом.

    Returns:
        ContactResponse: Оновлений контакт.
    """
    repo = ContactRepository(session)
    contact = await _get_contact_or_404(repo, contact_id, current_user)

    if (
        body.email != contact.email
        and await repo.get_by_email(body.email, current_user) is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Пошта '{body.email}' вже зайнята іншим контактом",
        )
    if (
        body.phone_number != contact.phone_number
        and await repo.get_by_phone(body.phone_number, current_user) is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Номер '{body.phone_number}' вже зайнятий іншим контактом",
        )

    updated = await repo.update(contact, body.model_dump())
    return ContactResponse.model_validate(updated)


@router.patch(
    "/{contact_id}",
    response_model=ContactResponse,
    responses={
        404: {"description": "Контакт не знайдено"},
        409: {"description": "Email або номер зайняті іншим контактом"},
    },
    summary="Часткове оновлення існуючого контакту",
)
async def update_contact_partial(
    body: ContactUpdate,
    current_user: CurrentUser,
    session: SessionDep,
    contact_id: int = ContactId,
) -> ContactResponse:
    """Часткове оновлення окремих полів контакту (PATCH).

    Args:
        body: Схема з полями, які необхідно змінити (непередані поля не змінюються).
        current_user: Поточний користувач-власник.
        session: Асинхронна сесія бази даних.
        contact_id: Числовий ідентифікатор контакту.

    Raises:
        HTTPException: 404 Not Found, якщо контакт не знайдено.
        HTTPException: 409 Conflict, якщо оновлюваний email або телефон вже зайняті.

    Returns:
        ContactResponse: Оновлений контакт.
    """
    repo = ContactRepository(session)
    contact = await _get_contact_or_404(repo, contact_id, current_user)

    fields = body.model_dump(exclude_unset=True)
    if not fields:
        return ContactResponse.model_validate(contact)

    if (
        "email" in fields
        and fields["email"] != contact.email
        and await repo.get_by_email(fields["email"], current_user) is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Пошта '{fields['email']}' вже зайнята іншим контактом",
        )

    if (
        "phone_number" in fields
        and fields["phone_number"] != contact.phone_number
        and await repo.get_by_phone(fields["phone_number"], current_user) is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Номер '{fields['phone_number']}' вже зайнятий іншим контактом",
        )

    updated = await repo.update(contact, fields)
    return ContactResponse.model_validate(updated)


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Контакт не знайдено"}},
    summary="Видалити контакт",
)
async def delete_contact(
    current_user: CurrentUser,
    session: SessionDep,
    contact_id: int = ContactId,
) -> None:
    """Видалення контакту за його числовим ідентифікатором.

    Args:
        current_user: Поточний автентифікований користувач-власник.
        session: Асинхронна сесія бази даних.
        contact_id: Числовий ідентифікатор контакту.

    Raises:
        HTTPException: 404 Not Found, якщо контакт не існує або належить іншому юзеру.
    """
    repo = ContactRepository(session)
    contact = await _get_contact_or_404(repo, contact_id, current_user)
    await repo.delete(contact)
