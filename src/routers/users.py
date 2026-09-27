"""Роутер користувача: інформація про поточного юзера (/me з лімітом) та аватар з контролем ролей (RBAC)."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from ..dependencies import CurrentUser, SessionDep
from ..models import UserRole
from ..repository import UserRepository
from ..schemas import UserResponse
from ..services.cache import cache_service
from ..services.upload_file import UploadFileService

router = APIRouter(prefix="/api/users", tags=["users"])
limiter = Limiter(key_func=get_remote_address)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Отримати профіль поточного автентифікованого користувача",
    description="Обмежено до 10 запитів на хвилину за допомогою SlowAPI.",
)
@limiter.limit("10/minute")
async def get_me(request: Request, current_user: CurrentUser) -> UserResponse:
    """Повертає профіль поточного авторизованого користувача.

    Частота звернення до цього ендпоінта обмежена до 10 запитів на хвилину для кожного клієнта.

    Args:
        request: HTTP-запит FastAPI для роботи механізму Rate Limiting.
        current_user: Поточний автентифікований користувач із токена/кешу.

    Returns:
        UserResponse: Публічні дані облікового запису користувача.
    """
    return current_user


@router.patch(
    "/avatar",
    response_model=UserResponse,
    responses={
        403: {"description": "Зміна аватара дозволена лише адміністраторам"},
    },
    summary="Оновити аватар користувача через Cloudinary (тільки Admin)",
    description="Доступ до зміни аватара обмежено роллю Admin відповідно до вимог ТЗ.",
)
async def update_avatar(
    current_user: CurrentUser,
    session: SessionDep,
    file: UploadFile = File(..., description="Файл зображення аватара"),
) -> UserResponse:
    """Завантажує новий аватар користувача в хмарне сховище Cloudinary.

    Відповідно до технічних умов доступ до цієї операції дозволено лише
    користувачам із роллю `admin`. Звичайний користувач отримує помилку 403 Forbidden.

    Args:
        current_user: Поточний автентифікований користувач.
        session: Сесія бази даних SQLAlchemy.
        file: Завантажений файл зображення аватара.

    Raises:
        HTTPException: 403 Forbidden, якщо користувач не має ролі адміністратора.

    Returns:
        UserResponse: Оновлені дані користувача з новим URL аватара.
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Зміна аватара дозволена лише адміністраторам",
        )

    avatar_url = UploadFileService().upload_file(file, current_user.username)
    user = await UserRepository(session).update_avatar(current_user.email, avatar_url)
    await cache_service.invalidate_user(current_user.email)
    return user
