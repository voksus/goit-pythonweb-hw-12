"""Сервіс кешування даних у Redis: клієнт, життєвий цикл та робота з користувачами."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

import redis.asyncio as redis

from ..models import User, UserRole
from ..settings import settings

logger = logging.getLogger(__name__)

# Глобальний клієнт Redis (Singleton)
redis_client: redis.Redis | None = None


def get_redis_client() -> redis.Redis:
    """Отримання або лінива ініціалізація клієнта Redis.

    Створює екземпляр асинхронного клієнта Redis із параметрами конфігурації
    (хост, порт, пароль) та автоматичним декодуванням рядкових відповідей.

    Returns:
        redis.Redis: Екземпляр асинхронного клієнта Redis.
    """
    global redis_client
    if redis_client is None:
        password = (
            settings.redis_password.get_secret_value()
            if settings.redis_password
            else None
        )
        redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=password,
            decode_responses=True,
        )
    return redis_client


async def close_redis_client() -> None:
    """Коректне закриття пулу з'єднань Redis під час завершення роботи застосунку."""
    global redis_client
    if redis_client is not None:
        await redis_client.close()
        redis_client = None


class CacheService:
    """Сервіс для кешування, отримання та інвалідації сутностей User у Redis."""

    def __init__(self, client: redis.Redis | None = None) -> None:
        """Ініціалізація сервісу кешування.

        Args:
            client: Необов'язковий екземпляр клієнта Redis (корисно для моків у тестах).
        """
        self._client = client

    @property
    def client(self) -> redis.Redis:
        """Отримання активного екземпляра Redis клієнта.

        Returns:
            redis.Redis: Клієнт Redis.
        """
        if self._client is not None:
            return self._client
        return get_redis_client()

    def _make_key(self, email: str) -> str:
        """Генерація стандартизованого ключа кешу користувача.

        Args:
            email: Електронна пошта користувача.

        Returns:
            str: Ключ для Redis у форматі 'user:<email>'.
        """
        return f"user:{email.strip().lower()}"

    def _serialize_user(self, user: User) -> str:
        """Серіалізація сутності User у JSON-рядок для збереження в Redis.

        Args:
            user: Екземпляр ORM-моделі User.

        Returns:
            str: JSON-рядок з атрибутами користувача.
        """
        role_value = (
            user.role.value if isinstance(user.role, UserRole) else str(user.role)
        )
        user_dict: dict[str, Any] = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "hashed_password": user.hashed_password,
            "avatar_url": user.avatar_url,
            "role": role_value,
            "confirmed": user.confirmed,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "updated_at": user.updated_at.isoformat() if user.updated_at else None,
        }
        return json.dumps(user_dict)

    def _deserialize_user(self, user_json: str) -> User:
        """Десеріалізація JSON-рядка у відокремлену сутність моделі User.

        Args:
            user_json: JSON-рядок з даними користувача.

        Returns:
            User: Відтворений екземпляр моделі User.
        """
        data: dict[str, Any] = json.loads(user_json)
        return User(
            id=data["id"],
            username=data["username"],
            email=data["email"],
            hashed_password=data["hashed_password"],
            avatar_url=data.get("avatar_url"),
            role=UserRole(data["role"])
            if isinstance(data["role"], str)
            else data["role"],
            confirmed=data["confirmed"],
            created_at=(
                datetime.fromisoformat(data["created_at"])
                if data.get("created_at")
                else None
            ),
            updated_at=(
                datetime.fromisoformat(data["updated_at"])
                if data.get("updated_at")
                else None
            ),
        )

    async def get_user(self, email: str) -> User | None:
        """Отримання сутності користувача з кешу Redis за адресою пошти.

        Args:
            email: Електронна пошта користувача.

        Returns:
            User | None: Об'єкт User, якщо ключ знайдено, інакше None.
        """
        key = self._make_key(email)
        try:
            cached_data = await self.client.get(key)
            if not cached_data:
                return None
            return self._deserialize_user(cached_data)
        except Exception as exc:
            logger.warning(
                "Помилка зчитування користувача %s з Redis кешу: %s", key, exc
            )
            return None

    async def set_user(self, user: User, expire_minutes: int | None = None) -> None:
        """Збереження користувача в кеш Redis зі встановленням TTL.

        Args:
            user: Екземпляр User для кешування.
            expire_minutes: Час життя кешу у хвилинах (за замовчуванням береться із settings).
        """
        key = self._make_key(user.email)
        minutes = expire_minutes or settings.redis_cache_expire_minutes
        ttl_seconds = minutes * 60
        try:
            serialized = self._serialize_user(user)
            await self.client.set(key, serialized, ex=ttl_seconds)
        except Exception as exc:
            logger.warning("Помилка запису користувача %s до Redis кешу: %s", key, exc)

    async def invalidate_user(self, email: str) -> None:
        """Видалення користувача з кешу Redis (інвалідація).

        Args:
            email: Електронна пошта користувача для інвалідації.
        """
        key = self._make_key(email)
        try:
            await self.client.delete(key)
        except Exception as exc:
            logger.warning("Помилка інвалідації кешу для %s в Redis: %s", key, exc)


cache_service = CacheService()
