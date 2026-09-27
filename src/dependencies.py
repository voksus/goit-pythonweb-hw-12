"""Спільні аліаси залежностей для лаконічних сигнатур роутерів."""

from typing import Annotated

import redis.asyncio as redis
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db
from .models import User
from .services.cache import get_redis_client
from .services.security import auth_service

#: Аліас типу для отримання асинхронної сесії SQLAlchemy у роутерах.
SessionDep = Annotated[AsyncSession, Depends(get_db)]

#: Аліас типу для отримання поточного авторизованого користувача з токена або Redis-кешу.
CurrentUser = Annotated[User, Depends(auth_service.get_current_user)]

#: Аліас типу для отримання екземпляра асинхронного клієнта Redis.
RedisDep = Annotated[redis.Redis, Depends(get_redis_client)]
