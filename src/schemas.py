"""Pydantic-схеми валідації запитів та відповідей API."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from .models import UserRole

# --- Схеми користувачів та безпеки ---


class UserCreate(BaseModel):
    """Схема валідації вхідних даних для реєстрації нового користувача."""

    username: str = Field(
        ..., min_length=3, max_length=50, description="Ім'я користувача"
    )
    email: EmailStr = Field(..., description="Електронна пошта")
    password: str = Field(..., min_length=6, max_length=128, description="Пароль")


class UserResponse(BaseModel):
    """Схема відповіді з публічними даними користувача (без хешу пароля)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    email: EmailStr
    avatar_url: str | None
    role: UserRole
    confirmed: bool
    created_at: datetime


class Token(BaseModel):
    """Схема відповіді з парою JWT токенів (access та refresh)."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenRefreshRequest(BaseModel):
    """Схема запиту на оновлення access-токена за допомогою refresh-токена."""

    refresh_token: str = Field(..., description="JWT refresh токен")


class RequestEmail(BaseModel):
    """Схема повторного запиту листа для верифікації електронної пошти."""

    email: EmailStr


class RequestPasswordReset(BaseModel):
    """Схема запиту на ініціалізацію процедури скидання пароля користувача."""

    email: EmailStr = Field(
        ..., description="Електронна пошта зареєстрованого користувача"
    )


class ResetPasswordConfirm(BaseModel):
    """Схема підтвердження скидання пароля з новим паролем і токеном."""

    token: str = Field(..., description="Одноразовий токен скидання пароля")
    new_password: str = Field(
        ..., min_length=6, max_length=128, description="Новий пароль користувача"
    )


class MessageResponse(BaseModel):
    """Уніфікована схема інформаційного повідомлення API."""

    message: str


# --- Схеми контактів ---


class ContactBase(BaseModel):
    """Базові атрибути сутності контакту."""

    first_name: str = Field(..., min_length=1, max_length=50)
    last_name: str = Field(..., min_length=1, max_length=50)
    email: EmailStr
    phone_number: str = Field(..., min_length=5, max_length=30)
    birthday: date
    extra_data: str | None = Field(default=None, max_length=500)


class ContactCreate(ContactBase):
    """Схема вхідних даних для створення нового контакту."""

    pass


class ContactUpdate(BaseModel):
    """Схема даних для часткового або повного оновлення контакту."""

    first_name: str | None = Field(default=None, min_length=1, max_length=50)
    last_name: str | None = Field(default=None, min_length=1, max_length=50)
    email: EmailStr | None = Field(default=None)
    phone_number: str | None = Field(default=None, min_length=5, max_length=30)
    birthday: date | None = Field(default=None)
    extra_data: str | None = Field(default=None, max_length=500)


class ContactResponse(ContactBase):
    """Схема повернення даних контакту клієнту з бази даних."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    created_at: datetime
    updated_at: datetime


class HealthCheck(BaseModel):
    """Схема відповіді перевірки стану доступності сервісу (Health Check)."""

    status: str
    database: str
