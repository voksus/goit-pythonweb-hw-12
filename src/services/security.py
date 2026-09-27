"""Сервіс безпеки: хешування паролів, видача та перевірка JWT-токенів (access, refresh, reset, verify)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import User
from ..repository import UserRepository
from ..settings import settings
from .cache import cache_service


class AuthService:
    """Інкапсуляція операцій криптографії та верифікації JWT."""

    ALGORITHM = "HS256"
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

    CREDENTIALS_EXCEPTION = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не вдалося валідувати облікові дані",
        headers={"WWW-Authenticate": "Bearer"},
    )

    async def hash_password(self, password: str) -> str:
        """Хешування відкритого пароля за допомогою bcrypt.

        Args:
            password: Пароль у відкритому вигляді.

        Returns:
            str: Сформований безпечний хеш пароля.
        """
        return self.pwd_context.hash(password)

    async def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Перевірка відповідності відкритого пароля збереженому хешу.

        Args:
            plain_password: Пароль у відкритому вигляді.
            hashed_password: Хеш пароля з бази даних.

        Returns:
            bool: True, якщо пароль валідний, інакше False.
        """
        return self.pwd_context.verify(plain_password, hashed_password)

    async def _create_token(self, email: str, scope: str, expires_minutes: int) -> str:
        """Внутрішній метод генерації підписаного JWT токена із заданим scope та терміном дії.

        Args:
            email: Електронна пошта користувача (sub).
            scope: Тип призначення токена.
            expires_minutes: Термін дії токена у хвилинах.

        Returns:
            str: Закодований рядок токена.
        """
        payload = {
            "sub": email,
            "scope": scope,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=expires_minutes),
        }
        return jwt.encode(
            payload, settings.secret_key.get_secret_value(), algorithm=self.ALGORITHM
        )

    async def create_access_token(
        self, email: str, expires_minutes: int | None = None
    ) -> str:
        """Генерація короткоживучого JWT токена доступу (access token).

        Args:
            email: Електронна пошта користувача (sub).
            expires_minutes: Час життя токена у хвилинах (за замовчуванням із settings).

        Returns:
            str: Закодований JWT access токен.
        """
        return await self._create_token(
            email,
            "access_token",
            expires_minutes or settings.access_token_expire_minutes,
        )

    async def create_refresh_token(
        self, email: str, expires_days: int | None = None
    ) -> str:
        """Генерація довгоживучого JWT токена оновлення (refresh token).

        Args:
            email: Електронна пошта користувача (sub).
            expires_days: Час життя токена в днях (за замовчуванням із settings).

        Returns:
            str: Закодований JWT refresh токен.
        """
        days = expires_days or settings.refresh_token_expire_days
        expires_minutes = days * 24 * 60
        return await self._create_token(email, "refresh_token", expires_minutes)

    async def decode_refresh_token(self, token: str) -> str:
        """Декодування та валідація JWT токена оновлення (refresh token).

        Args:
            token: Закодований JWT refresh токен.

        Raises:
            HTTPException: 401 Unauthorized, якщо токен недійсний, прострочений або має хибний scope.

        Returns:
            str: Електронна пошта користувача (sub).
        """
        try:
            payload = jwt.decode(
                token,
                settings.secret_key.get_secret_value(),
                algorithms=[self.ALGORITHM],
            )
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недійсний або прострочений refresh токен",
                headers={"WWW-Authenticate": "Bearer"},
            ) from exc

        if payload.get("scope") != "refresh_token":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недійсний тип (scope) токена",
                headers={"WWW-Authenticate": "Bearer"},
            )
        email: str | None = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="У токені відсутній суб'єкт (email)",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return email

    async def create_verification_token(self, email: str) -> str:
        """Генерація токена верифікації адреси електронної пошти.

        Args:
            email: Електронна пошта користувача.

        Returns:
            str: Одноразовий токен активації облікового запису.
        """
        return await self._create_token(
            email, "verification_token", settings.verification_token_expire_minutes
        )

    async def decode_verification_token(self, token: str) -> str:
        """Декодування та перевірка токена верифікації електронної пошти.

        Args:
            token: Закодований токен підтвердження пошти.

        Raises:
            HTTPException: 422 Unprocessable Entity або 401 Unauthorized при невалідному токені.

        Returns:
            str: Електронна пошта користувача.
        """
        try:
            payload = jwt.decode(
                token,
                settings.secret_key.get_secret_value(),
                algorithms=[self.ALGORITHM],
            )
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Недійсний токен для верифікації пошти",
            ) from exc

        if payload.get("scope") != "verification_token":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Недійсний тип (scope) токена",
            )
        email: str | None = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="У токені відсутній суб'єкт (email)",
            )
        return email

    async def create_password_reset_token(self, email: str) -> str:
        """Генерація короткоживучого токена для скидання пароля.

        Args:
            email: Електронна пошта користувача.

        Returns:
            str: Одноразовий токен скидання пароля.
        """
        return await self._create_token(
            email, "password_reset", settings.password_reset_token_expire_minutes
        )

    async def decode_password_reset_token(self, token: str) -> str:
        """Декодування та валідація токена для скидання пароля.

        Args:
            token: Одноразовий токен скидання пароля.

        Raises:
            HTTPException: 400 Bad Request, якщо токен недійсний, закінчився його термін дії або невірний scope.

        Returns:
            str: Електронна пошта користувача.
        """
        try:
            payload = jwt.decode(
                token,
                settings.secret_key.get_secret_value(),
                algorithms=[self.ALGORITHM],
            )
        except JWTError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недійсний або прострочений токен для скидання пароля",
            ) from exc

        if payload.get("scope") != "password_reset":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Недійсний тип (scope) токена",
            )
        email: str | None = payload.get("sub")
        if email is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="У токені відсутній суб'єкт (email)",
            )
        return email

    async def get_current_user(
        self,
        token: str = Depends(oauth2_scheme),
        session: AsyncSession = Depends(get_db),
    ) -> User:
        """Отримання сутності поточного авторизованого користувача за токеном доступу.

        Спершу перевіряється наявність користувача в кеші Redis. Якщо запис відсутній,
        відбувається запит до PostgreSQL із подальшим кешуванням отриманої сутності.

        Args:
            token: Bearer JWT access токен із заголовка авторизації.
            session: Асинхронна сесія бази даних.

        Raises:
            HTTPException: 401 Unauthorized, якщо токен недійсний або користувача не знайдено.

        Returns:
            User: Екземпляр моделі авторизованого користувача.
        """
        try:
            payload = jwt.decode(
                token,
                settings.secret_key.get_secret_value(),
                algorithms=[self.ALGORITHM],
            )
            if payload.get("scope") != "access_token":
                raise self.CREDENTIALS_EXCEPTION
            email: str | None = payload.get("sub")
            if email is None:
                raise self.CREDENTIALS_EXCEPTION
        except JWTError as exc:
            raise self.CREDENTIALS_EXCEPTION from exc

        # 1. Спроба отримати користувача з Redis-кешу
        cached_user = await cache_service.get_user(email)
        if cached_user is not None:
            return cached_user

        # 2. Якщо в кеші відсутній — запит до бази даних PostgreSQL
        user = await UserRepository(session).get_by_email(email)
        if user is None:
            raise self.CREDENTIALS_EXCEPTION

        # 3. Збереження щойно отриманого користувача в кеш Redis
        await cache_service.set_user(user)
        return user


auth_service = AuthService()
