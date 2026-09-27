"""Роутер автентифікації: реєстрація, логін, пара токенів, скидання пароля та підтвердження пошти."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from ..dependencies import SessionDep
from ..repository import UserRepository
from ..schemas import (
    MessageResponse,
    RequestEmail,
    RequestPasswordReset,
    ResetPasswordConfirm,
    Token,
    TokenRefreshRequest,
    UserCreate,
    UserResponse,
)
from ..services.cache import cache_service
from ..services.mail import send_reset_password_email, send_verification_email
from ..services.security import auth_service

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        409: {"description": "Користувач з таким email або username вже існує"},
    },
    summary="Реєстрація нового користувача",
)
async def register(
    body: UserCreate,
    background_tasks: BackgroundTasks,
    request: Request,
    session: SessionDep,
) -> UserResponse:
    """Реєстрація нового користувача з автоматичною відправкою листа верифікації.

    Користувач створюється зі стандартною роллю 'user' та статусом confirmed=False.
    Лист для підтвердження електронної пошти відправляється асинхронно через BackgroundTasks.

    Args:
        body: Схема даних нового користувача (username, email, password).
        background_tasks: Менеджер фонових задач FastAPI для відправки листа.
        request: Об'єкт HTTP-запиту для отримання базового URL хоста.
        session: Асинхронна сесія бази даних.

    Raises:
        HTTPException: 409 Conflict, якщо email або username вже зайняті.

    Returns:
        UserResponse: Створений користувач без хешу пароля.
    """
    repo = UserRepository(session)
    if await repo.get_by_email(body.email) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Користувач з такою адресою електронної пошти вже зареєстрований",
        )
    if await repo.get_by_username(body.username) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Користувач з таким іменем вже існує",
        )

    hashed_pass = await auth_service.hash_password(body.password)
    user = await repo.create(
        username=body.username,
        email=body.email,
        hashed_password=hashed_pass,
    )

    background_tasks.add_task(
        send_verification_email, user.email, user.username, str(request.base_url)
    )
    return user


@router.post(
    "/login",
    response_model=Token,
    responses={
        401: {"description": "Невірні облікові дані або пошта не підтверджена"},
    },
    summary="Вхід у систему та отримання пари токенів (access та refresh)",
)
async def login(
    session: SessionDep,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    """Автентифікація користувача за логіном/email та паролем.

    Перевіряє правильність введених даних, статус підтвердження пошти,
    зберігає дані користувача у швидкий кеш Redis та генерує пару JWT-токенів
    (короткоживучий access_token та довгоживучий refresh_token).

    Args:
        session: Асинхронна сесія бази даних.
        form_data: Стандартна форма OAuth2 з полями username та password.

    Raises:
        HTTPException: 401 Unauthorized, якщо облікові дані невірні або пошта не підтверджена.

    Returns:
        Token: Схема з access_token, refresh_token та типом bearer.
    """
    repo = UserRepository(session)
    user = await repo.get_by_email(form_data.username)
    if not user:
        user = await repo.get_by_username(form_data.username)

    if not user or not await auth_service.verify_password(
        form_data.password, user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невірний логін або пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Електронна пошта не підтверджена",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Кешування користувача в Redis під час авторизації
    await cache_service.set_user(user)

    access_token = await auth_service.create_access_token(user.email)
    refresh_token = await auth_service.create_refresh_token(user.email)
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.post(
    "/refresh_token",
    response_model=Token,
    responses={
        401: {"description": "Недійсний refresh токен або користувача не знайдено"},
    },
    summary="Оновлення пари access та refresh токенів",
)
async def refresh_tokens(
    body: TokenRefreshRequest,
    session: SessionDep,
) -> Token:
    """Видача нової пари JWT-токенів за валідним refresh-токеном.

    Дозволяє клієнту оновити access-токен без повторного введення логіна і пароля.
    Також оновлює стан користувача в Redis-кеші.

    Args:
        body: Схема запиту, що містить refresh_token.
        session: Асинхронна сесія бази даних.

    Raises:
        HTTPException: 401 Unauthorized, якщо токен недійсний або користувача не знайдено.

    Returns:
        Token: Нова пара access та refresh токенів.
    """
    email = await auth_service.decode_refresh_token(body.refresh_token)
    repo = UserRepository(session)
    user = await repo.get_by_email(email)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Користувача не знайдено",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.confirmed:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Електронна пошта не підтверджена",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Оновлення даних користувача в кеші Redis
    await cache_service.set_user(user)

    access_token = await auth_service.create_access_token(user.email)
    refresh_token = await auth_service.create_refresh_token(user.email)
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


@router.get(
    "/confirmed_email/{token}",
    response_model=MessageResponse,
    summary="Підтвердження адреси електронної пошти за токеном",
)
async def confirmed_email(
    token: str,
    session: SessionDep,
) -> MessageResponse:
    """Активація облікового запису за одноразовим токеном верифікації.

    Args:
        token: Токен верифікації з URL-посилання в електронному листі.
        session: Асинхронна сесія бази даних.

    Raises:
        HTTPException: 400 Bad Request, якщо токен недійсний або користувача не знайдено.

    Returns:
        MessageResponse: Повідомлення про успішне підтвердження пошти.
    """
    email = await auth_service.decode_verification_token(token)
    repo = UserRepository(session)
    user = await repo.get_by_email(email)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Помилка верифікації: користувача не знайдено",
        )
    if user.confirmed:
        return MessageResponse(
            message="Ваша електронна пошта вже була підтверджена раніше"
        )

    await repo.confirm_email(email)
    await cache_service.invalidate_user(email)
    return MessageResponse(message="Електронну пошту успішно підтверджено")


@router.post(
    "/request_email",
    response_model=MessageResponse,
    summary="Повторний запит листа для верифікації пошти",
)
async def request_email(
    body: RequestEmail,
    background_tasks: BackgroundTasks,
    request: Request,
    session: SessionDep,
) -> MessageResponse:
    """Повторна відправка листа активації, якщо попередній лист було втрачено.

    Args:
        body: Схема запиту з адресою електронної пошти.
        background_tasks: Менеджер фонових задач.
        request: Об'єкт HTTP-запиту.
        session: Асинхронна сесія бази даних.

    Returns:
        MessageResponse: Уніфіковане інформаційне повідомлення.
    """
    repo = UserRepository(session)
    user = await repo.get_by_email(body.email)
    if user and not user.confirmed:
        background_tasks.add_task(
            send_verification_email, user.email, user.username, str(request.base_url)
        )
    return MessageResponse(
        message="Якщо обліковий запис існує і ще не підтверджений, лист для активації відправлено"
    )


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Запит на скидання пароля через електронну пошту",
)
async def forgot_password(
    body: RequestPasswordReset,
    background_tasks: BackgroundTasks,
    request: Request,
    session: SessionDep,
) -> MessageResponse:
    """Ініціалізація процедури безпечного скидання пароля.

    Якщо вказаний email зареєстрований і підтверджений, на нього надсилається лист з одноразовим токеном.
    Відповідь завжди повертає успіх задля запобігання витоку інформації про наявність адрес у системі.

    Args:
        body: Схема запиту з email користувача.
        background_tasks: Менеджер фонових задач FastAPI.
        request: Об'єкт HTTP-запиту.
        session: Асинхронна сесія бази даних.

    Returns:
        MessageResponse: Інформаційне повідомлення про відправку інструкцій.
    """
    repo = UserRepository(session)
    user = await repo.get_by_email(body.email)
    if user and user.confirmed:
        background_tasks.add_task(
            send_reset_password_email, user.email, user.username, str(request.base_url)
        )
    return MessageResponse(
        message="Якщо обліковий запис із такою поштою існує, лист із інструкціями для скидання пароля надіслано"
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    responses={
        400: {"description": "Недійсний токен або помилка скидання пароля"},
    },
    summary="Встановлення нового пароля за токеном скидання",
)
async def reset_password(
    body: ResetPasswordConfirm,
    session: SessionDep,
) -> MessageResponse:
    """Встановлення нового пароля користувача за валідним одноразовим токеном.

    Декодує токен зі scope 'password_reset', хешує новий пароль, оновлює запис у БД
    та інвалідує старий кеш користувача в Redis.

    Args:
        body: Схема з одноразовим токеном та новим паролем.
        session: Асинхронна сесія бази даних.

    Raises:
        HTTPException: 400 Bad Request, якщо токен недійсний, прострочений або користувача не знайдено.

    Returns:
        MessageResponse: Повідомлення про успішну зміну пароля.
    """
    email = await auth_service.decode_password_reset_token(body.token)
    repo = UserRepository(session)
    user = await repo.get_by_email(email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Користувача не знайдено",
        )

    hashed_password = await auth_service.hash_password(body.new_password)
    await repo.update_password(email, hashed_password)
    await cache_service.invalidate_user(email)
    return MessageResponse(
        message="Пароль успішно змінено. Тепер ви можете увійти з новим паролем"
    )
