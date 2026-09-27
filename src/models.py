"""ORM-моделі SQLAlchemy 2.0 для контактної книги, користувачів та ролей."""

from __future__ import annotations

import enum
from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    MetaData,
    String,
    Text,
    false,
    func,
)
from sqlalchemy import (
    Enum as SqlEnum,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Базовий декларативний клас, спільний для всіх ORM-моделей проєкту.

    Інкапсулює метадані з узгодженою конвенцією іменування індексів та обмежень (constraints).
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class UserRole(str, enum.Enum):
    """Ролі користувачів для системи розмежування доступу (RBAC)."""

    USER = "user"  #: Звичайний користувач із базовими правами доступу.
    ADMIN = "admin"  #: Адміністратор із розширеними правами (зокрема зміна власного аватара).


class User(Base):
    """Модель облікового запису користувача системи.

    Зберігає облікові дані для автентифікації, статус верифікації пошти,
    роль у системі та посилання на аватар.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(
        SqlEnum(
            UserRole,
            name="user_role",
            values_callable=lambda obj: [e.value for e in obj],
        ),
        default=UserRole.USER,
        server_default=UserRole.USER.value,
        nullable=False,
    )
    confirmed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    contacts: Mapped[list[Contact]] = relationship(
        "Contact", back_populates="user", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        """Рядкове представлення сутності користувача."""
        return f"<User #{self.id} {self.username} role={self.role.value} confirmed={self.confirmed}>"


class Contact(Base):
    """Модель контакту в базі даних.

    Зберігає персональну інформацію про контакт, що прив'язаний
    до конкретного зареєстрованого користувача (власника).
    """

    __tablename__ = "contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    first_name: Mapped[str] = mapped_column(String(50), index=True)
    last_name: Mapped[str] = mapped_column(String(50), index=True)
    email: Mapped[str] = mapped_column(String(100), index=True)
    phone_number: Mapped[str] = mapped_column(String(30), index=True)
    birthday: Mapped[date] = mapped_column(Date, nullable=False)
    extra_data: Mapped[str | None] = mapped_column(Text, nullable=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user: Mapped[User] = relationship("User", back_populates="contacts")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        """Рядкове представлення сутності контакту."""
        return f"<Contact #{self.id} {self.first_name} {self.last_name} user_id={self.user_id}>"
