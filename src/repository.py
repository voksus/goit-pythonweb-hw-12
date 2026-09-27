"""Шар доступу до даних (Repository) з ізоляцією контактів за користувачами."""

from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Contact, User
from .schemas import ContactCreate


class UserRepository:
    """Репозиторій для керування сутностями User у базі даних."""

    def __init__(self, session: AsyncSession) -> None:
        """Ініціалізація репозиторію користувачів.

        Args:
            session: Асинхронна сесія бази даних SQLAlchemy.
        """
        self.session = session

    async def get_by_id(self, user_id: int) -> User | None:
        """Пошук користувача за його первинним ключем (ID).

        Args:
            user_id: Числовий ідентифікатор користувача.

        Returns:
            User | None: Знайдений екземпляр User або None, якщо не знайдено.
        """
        return await self.session.scalar(select(User).where(User.id == user_id))

    async def get_by_email(self, email: str) -> User | None:
        """Пошук користувача за адресою електронної пошти.

        Args:
            email: Електронна пошта користувача.

        Returns:
            User | None: Знайдений користувач або None.
        """
        return await self.session.scalar(select(User).where(User.email == email))

    async def get_by_username(self, username: str) -> User | None:
        """Пошук користувача за унікальним іменем.

        Args:
            username: Ім'я користувача (username).

        Returns:
            User | None: Знайдений користувач або None.
        """
        return await self.session.scalar(select(User).where(User.username == username))

    async def create(self, username: str, email: str, hashed_password: str) -> User:
        """Створення нового користувача зі стандартною роллю 'user'.

        Args:
            username: Ім'я нового користувача.
            email: Електронна пошта.
            hashed_password: Хешований рядок пароля.

        Returns:
            User: Створений та оновлений екземпляр User.
        """
        user = User(username=username, email=email, hashed_password=hashed_password)
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def confirm_email(self, email: str) -> None:
        """Підтвердження адреси електронної пошти користувача.

        Встановлює прапорець confirmed=True для знайденого акаунту.

        Args:
            email: Електронна пошта користувача для активації.
        """
        user = await self.get_by_email(email)
        if user:
            user.confirmed = True
            await self.session.flush()

    async def update_avatar(self, email: str, avatar_url: str) -> User:
        """Оновлення посилання на аватар користувача.

        Args:
            email: Електронна пошта користувача.
            avatar_url: Новий URL аватара.

        Raises:
            ValueError: Якщо користувача з вказаною поштою не знайдено.

        Returns:
            User: Оновлений екземпляр користувача.
        """
        user = await self.get_by_email(email)
        if not user:
            raise ValueError(f"Користувача з email {email} не знайдено")
        user.avatar_url = avatar_url
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update_password(self, email: str, new_hashed_password: str) -> User:
        """Оновлення хешу пароля користувача за адресою електронної пошти.

        Args:
            email: Електронна пошта користувача.
            new_hashed_password: Новий хешований пароль.

        Raises:
            ValueError: Якщо користувача з вказаною поштою не знайдено.

        Returns:
            User: Оновлений екземпляр моделі користувача.
        """
        user = await self.get_by_email(email)
        if not user:
            raise ValueError(f"Користувача з email {email} не знайдено")
        user.hashed_password = new_hashed_password
        await self.session.flush()
        await self.session.refresh(user)
        return user


class ContactRepository:
    """Репозиторій для керування контактами поточного користувача."""

    def __init__(self, session: AsyncSession) -> None:
        """Ініціалізація репозиторію контактів.

        Args:
            session: Асинхронна сесія бази даних SQLAlchemy.
        """
        self.session = session

    async def ping(self) -> bool:
        """Перевірка доступності бази даних за допомогою тестового SQL-запиту.

        Returns:
            bool: True, якщо база успішно повернула 1, інакше False.
        """
        try:
            result = await self.session.scalar(select(text("1")))
            return result == 1
        except Exception:
            return False

    async def get_by_id(self, contact_id: int, user: User) -> Contact | None:
        """Отримання контакту за ID з обмеженням за поточним користувачем.

        Args:
            contact_id: Ідентифікатор шуканого контакту.
            user: Поточний автентифікований користувач-власник.

        Returns:
            Contact | None: Знайдений контакт або None.
        """
        return await self.session.scalar(
            select(Contact).where(Contact.id == contact_id, Contact.user_id == user.id)
        )

    async def get_by_email(self, email: str, user: User) -> Contact | None:
        """Пошук контакту за email серед контактів поточного користувача.

        Args:
            email: Пошта контакту.
            user: Користувач-власник контакту.

        Returns:
            Contact | None: Знайдений контакт або None.
        """
        return await self.session.scalar(
            select(Contact).where(Contact.email == email, Contact.user_id == user.id)
        )

    async def get_by_phone(self, phone_number: str, user: User) -> Contact | None:
        """Пошук контакту за номером телефону серед контактів поточного користувача.

        Args:
            phone_number: Номер телефону контакту.
            user: Користувач-власник контакту.

        Returns:
            Contact | None: Знайдений контакт або None.
        """
        return await self.session.scalar(
            select(Contact).where(
                Contact.phone_number == phone_number, Contact.user_id == user.id
            )
        )

    async def list_contacts(
        self,
        user: User,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        email: str | None = None,
    ) -> list[Contact]:
        """Отримання списку контактів із пагінацією та гнучкою фільтрацією.

        Args:
            user: Користувач-власник контактів.
            skip: Кількість записів для пропуску (пагінація).
            limit: Максимальна кількість записів у вибірці.
            search: Рядок для загального нечутливого до регістру пошуку (ім'я, прізвище, email).
            first_name: Фільтр за ім'ям контакту.
            last_name: Фільтр за прізвищем контакту.
            email: Фільтр за адресою пошти контакту.

        Returns:
            list[Contact]: Список знайдених контактів.
        """
        stmt = select(Contact).where(Contact.user_id == user.id)
        conditions = []

        if search:
            pattern = f"%{search}%"
            conditions.append(
                or_(
                    Contact.first_name.ilike(pattern),
                    Contact.last_name.ilike(pattern),
                    Contact.email.ilike(pattern),
                )
            )

        if first_name:
            conditions.append(Contact.first_name.ilike(f"%{first_name}%"))
        if last_name:
            conditions.append(Contact.last_name.ilike(f"%{last_name}%"))
        if email:
            conditions.append(Contact.email.ilike(f"%{email}%"))

        if conditions:
            stmt = stmt.where(*conditions)

        stmt = stmt.order_by(Contact.id.asc()).offset(skip).limit(limit)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def create(self, body: ContactCreate, user: User) -> Contact:
        """Створення нового контакту для поточного користувача.

        Args:
            body: Схема даних для створення контакту.
            user: Поточний користувач-власник.

        Returns:
            Contact: Створений та оновлений екземпляр контакту.
        """
        contact = Contact(**body.model_dump(), user_id=user.id)
        self.session.add(contact)
        await self.session.flush()
        await self.session.refresh(contact)
        return contact

    async def update(self, contact: Contact, fields: dict[str, Any]) -> Contact:
        """Оновлення полів наявного контакту.

        Args:
            contact: Екземпляр контакту для оновлення.
            fields: Словник оновлюваних полів та їх значень.

        Returns:
            Contact: Оновлений екземпляр контакту.
        """
        for key, value in fields.items():
            setattr(contact, key, value)
        await self.session.flush()
        await self.session.refresh(contact)
        return contact

    async def delete(self, contact: Contact) -> None:
        """Видалення контакту з бази даних.

        Args:
            contact: Екземпляр контакту для видалення.
        """
        await self.session.delete(contact)
        await self.session.flush()

    async def get_upcoming_birthdays(self, user: User, days: int = 7) -> list[Contact]:
        """Пошук контактів, день народження яких настає впродовж наступних N днів.

        Коректно враховує перехід через межу нового календарного року та високосні дати (29 лютого).

        Args:
            user: Користувач-власник контактів.
            days: Кількість днів вперед для розрахунку (за замовчуванням 7).

        Returns:
            list[Contact]: Відсортований за хронологією настання список контактів.
        """
        today = date.today()
        result = await self.session.scalars(
            select(Contact).where(Contact.user_id == user.id)
        )
        contacts = list(result.all())

        upcoming_with_dates: list[tuple[date, Contact]] = []
        for contact in contacts:
            bdate = contact.birthday
            try:
                bday_this_year = bdate.replace(year=today.year)
            except ValueError:
                bday_this_year = date(today.year, 2, 28)

            if bday_this_year < today:
                try:
                    next_bday = bdate.replace(year=today.year + 1)
                except ValueError:
                    next_bday = date(today.year + 1, 2, 28)
            else:
                next_bday = bday_this_year

            delta_days = (next_bday - today).days
            if 0 <= delta_days <= days:
                upcoming_with_dates.append((next_bday, contact))

        upcoming_with_dates.sort(key=lambda item: item[0])
        return [contact for _, contact in upcoming_with_dates]
