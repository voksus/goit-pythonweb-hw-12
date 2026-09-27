"""Інтеграційні тести CRUD операцій контактів, пошуку, пагінації, ізоляції та днів народження."""

from datetime import date, timedelta

import pytest
from httpx import AsyncClient


@pytest.fixture
def contact_payload() -> dict[str, str]:
    """Базові дані для створення контакту."""
    return {
        "first_name": "Taras",
        "last_name": "Shevchenko",
        "email": "taras@kobzar.ua",
        "phone_number": "+380501112233",
        "birthday": "1990-03-09",
        "extra_data": "Poet and artist",
    }


@pytest.mark.asyncio
async def test_create_contact_success(
    client: AsyncClient,
    user_token_headers: dict[str, str],
    contact_payload: dict[str, str],
) -> None:
    """Успішне створення нового контакту повертає 201 Created."""
    response = await client.post(
        "/api/contacts", json=contact_payload, headers=user_token_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["first_name"] == contact_payload["first_name"]
    assert data["email"] == contact_payload["email"]
    assert "id" in data
    assert "user_id" in data


@pytest.mark.asyncio
async def test_create_contact_duplicate_email(
    client: AsyncClient,
    user_token_headers: dict[str, str],
    contact_payload: dict[str, str],
) -> None:
    """Спроба створити контакт з уже наявним email повертає 409 Conflict."""
    await client.post("/api/contacts", json=contact_payload, headers=user_token_headers)

    duplicate_payload = contact_payload.copy()
    duplicate_payload["phone_number"] = "+380509998877"

    response = await client.post(
        "/api/contacts", json=duplicate_payload, headers=user_token_headers
    )
    assert response.status_code == 409
    assert "вже існує" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_contact_duplicate_phone(
    client: AsyncClient,
    user_token_headers: dict[str, str],
    contact_payload: dict[str, str],
) -> None:
    """Спроба створити контакт з уже наявним номером телефону повертає 409 Conflict."""
    await client.post("/api/contacts", json=contact_payload, headers=user_token_headers)

    duplicate_payload = contact_payload.copy()
    duplicate_payload["email"] = "other_taras@kobzar.ua"

    response = await client.post(
        "/api/contacts", json=duplicate_payload, headers=user_token_headers
    )
    assert response.status_code == 409
    assert "вже існує" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_contacts_and_search(
    client: AsyncClient,
    user_token_headers: dict[str, str],
    contact_payload: dict[str, str],
) -> None:
    """Отримання списку контактів, пагінація та пошук за ім'ям або поштою."""
    # Створюємо 2 контакти
    await client.post("/api/contacts", json=contact_payload, headers=user_token_headers)

    c2 = contact_payload.copy()
    c2["first_name"] = "Ivan"
    c2["email"] = "ivan@franko.ua"
    c2["phone_number"] = "+380507776655"
    await client.post("/api/contacts", json=c2, headers=user_token_headers)

    # Запит усіх контактів
    res_all = await client.get("/api/contacts", headers=user_token_headers)
    assert res_all.status_code == 200
    assert len(res_all.json()) == 2

    # Пошук за рядком "Ivan"
    res_search = await client.get(
        "/api/contacts?search=Ivan", headers=user_token_headers
    )
    assert res_search.status_code == 200
    assert len(res_search.json()) == 1
    assert res_search.json()[0]["first_name"] == "Ivan"

    # Пагінація limit=1
    res_page = await client.get("/api/contacts?limit=1", headers=user_token_headers)
    assert res_page.status_code == 200
    assert len(res_page.json()) == 1


@pytest.mark.asyncio
async def test_get_contact_by_id_and_user_isolation(
    client: AsyncClient,
    user_token_headers: dict[str, str],
    second_user_token_headers: dict[str, str],
    contact_payload: dict[str, str],
) -> None:
    """Перевірка повної ізоляції контактів: користувач В не може бачити контакт користувача А."""
    # Користувач А створює контакт
    res = await client.post(
        "/api/contacts", json=contact_payload, headers=user_token_headers
    )
    contact_id = res.json()["id"]

    # Користувач А успішно відкриває свій контакт
    res_owner = await client.get(
        f"/api/contacts/{contact_id}", headers=user_token_headers
    )
    assert res_owner.status_code == 200
    assert res_owner.json()["id"] == contact_id

    # Користувач В намагається отримати цей же контакт -> 404 Not Found!
    res_alien = await client.get(
        f"/api/contacts/{contact_id}", headers=second_user_token_headers
    )
    assert res_alien.status_code == 404


@pytest.mark.asyncio
async def test_update_contact_full_put(
    client: AsyncClient,
    user_token_headers: dict[str, str],
    contact_payload: dict[str, str],
) -> None:
    """Повне оновлення (PUT) контакту."""
    res = await client.post(
        "/api/contacts", json=contact_payload, headers=user_token_headers
    )
    contact_id = res.json()["id"]

    updated_data = {
        "first_name": "Taras_Updated",
        "last_name": "Shevchenko_Updated",
        "email": "updated@kobzar.ua",
        "phone_number": "+380509999999",
        "birthday": "1990-03-09",
        "extra_data": "Updated notes",
    }
    put_res = await client.put(
        f"/api/contacts/{contact_id}",
        json=updated_data,
        headers=user_token_headers,
    )

    assert put_res.status_code == 200
    assert put_res.json()["first_name"] == "Taras_Updated"
    assert put_res.json()["email"] == "updated@kobzar.ua"


@pytest.mark.asyncio
async def test_update_contact_partial_patch(
    client: AsyncClient,
    user_token_headers: dict[str, str],
    contact_payload: dict[str, str],
) -> None:
    """Часткове оновлення (PATCH) окремого поля контакту."""
    res = await client.post(
        "/api/contacts", json=contact_payload, headers=user_token_headers
    )
    contact_id = res.json()["id"]

    patch_res = await client.patch(
        f"/api/contacts/{contact_id}",
        json={"phone_number": "+380998887766"},
        headers=user_token_headers,
    )

    assert patch_res.status_code == 200
    assert patch_res.json()["phone_number"] == "+380998887766"
    assert patch_res.json()["first_name"] == contact_payload["first_name"]


@pytest.mark.asyncio
async def test_delete_contact_lifecycle(
    client: AsyncClient,
    user_token_headers: dict[str, str],
    contact_payload: dict[str, str],
) -> None:
    """Видалення контакту повертає 204 No Content, а наступний запит 404."""
    res = await client.post(
        "/api/contacts", json=contact_payload, headers=user_token_headers
    )
    contact_id = res.json()["id"]

    del_res = await client.delete(
        f"/api/contacts/{contact_id}", headers=user_token_headers
    )
    assert del_res.status_code == 204

    get_res = await client.get(
        f"/api/contacts/{contact_id}", headers=user_token_headers
    )
    assert get_res.status_code == 404


@pytest.mark.asyncio
async def test_get_upcoming_birthdays_route(
    client: AsyncClient,
    user_token_headers: dict[str, str],
    contact_payload: dict[str, str],
) -> None:
    """Ендпоінт /birthdays повертає контакти з днями народження у найближчі 7 днів."""
    today = date.today()

    # 1. Контакт із ДН через 4 дні (входить у 7 днів)
    c_soon = contact_payload.copy()
    target_soon = today + timedelta(days=4)
    bdate_soon = target_soon.replace(year=target_soon.year - 20)
    c_soon["email"] = "soon@example.com"
    c_soon["phone_number"] = "+380501110001"
    c_soon["birthday"] = bdate_soon.isoformat()
    await client.post("/api/contacts", json=c_soon, headers=user_token_headers)

    # 2. Контакт із ДН через 20 днів (не входить у 7 днів)
    c_far = contact_payload.copy()
    target_far = today + timedelta(days=20)
    bdate_far = target_far.replace(year=target_far.year - 20)
    c_far["email"] = "far@example.com"
    c_far["phone_number"] = "+380501110002"
    c_far["birthday"] = bdate_far.isoformat()
    await client.post("/api/contacts", json=c_far, headers=user_token_headers)

    res = await client.get("/api/contacts/birthdays", headers=user_token_headers)
    assert res.status_code == 200
    contacts = res.json()
    assert len(contacts) == 1
    assert contacts[0]["email"] == "soon@example.com"
