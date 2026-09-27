"""Сервіс вихідної пошти для верифікації користувачів та скидання пароля."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi_mail.errors import ConnectionErrors

from ..settings import settings
from .security import auth_service

logger = logging.getLogger(__name__)

TEMPLATE_FOLDER = Path(__file__).resolve().parent.parent / "templates"

conf = ConnectionConfig(
    MAIL_USERNAME=settings.mail_username,
    MAIL_PASSWORD=settings.mail_password.get_secret_value(),
    MAIL_FROM=settings.mail_from,
    MAIL_PORT=settings.mail_port,
    MAIL_SERVER=settings.mail_server,
    MAIL_FROM_NAME=settings.mail_from_name,
    MAIL_STARTTLS=settings.mail_starttls,
    MAIL_SSL_TLS=settings.mail_ssl_tls,
    USE_CREDENTIALS=settings.mail_use_credentials,
    VALIDATE_CERTS=settings.mail_validate_certs,
    TEMPLATE_FOLDER=TEMPLATE_FOLDER,
)

mailer = FastMail(conf)


async def send_verification_email(email: str, username: str, host: str) -> None:
    """Генерація токена та відправка електронного листа для верифікації пошти.

    Підтримує режим локальної емуляції (`mail_simulate`), вивід посилання в логи
    або повноцінне надсилання HTML-шаблону через поштовий сервер (Mailpit).

    Args:
        email: Електронна пошта адресата.
        username: Ім'я користувача для персоналізації тексту листа.
        host: Базовий URL хоста для формування клікабельного посилання.
    """
    token = await auth_service.create_verification_token(email)
    verify_url = f"{host}api/auth/confirmed_email/{token}"

    # Режим локальної симуляції (без затримок і без зовнішнього SMTP)
    if settings.mail_simulate:
        print(f"\n✉️  [MOCK EMAIL] Імітація надсилання листа на адресу: {email}")
        print(f"🔗 Посилання активації: {verify_url}\n")
        return

    # Якщо симуляція вимкнена, але увімкнено показ посилання в логах
    if settings.debug_show_token_in_logs:
        print(f"\n🔗 [DEV TOKEN URL]: {verify_url}\n")

    message = MessageSchema(
        subject="Підтвердження адреси електронної пошти",
        recipients=[email],
        template_body={
            "host": host,
            "username": username,
            "token": token,
            "expires_minutes": settings.verification_token_expire_minutes,
        },
        subtype=MessageType.html,
    )
    try:
        await mailer.send_message(message, template_name="email/verify_email.html")
    except ConnectionErrors as err:
        logger.warning(
            "Не вдалося відправити лист верифікації на адресу %s (SMTP недоступний): %s",
            email,
            err,
        )


async def send_reset_password_email(email: str, username: str, host: str) -> None:
    """Генерація токена та відправка електронного листа для скидання пароля.

    Формує короткоживучий токен (15 хвилин), генерує URL відновлення та
    надсилає персоналізований HTML-лист.

    Args:
        email: Електронна пошта одержувача.
        username: Ім'я користувача для персоналізованого звернення.
        host: Базовий URL хоста сервісу.
    """
    token = await auth_service.create_password_reset_token(email)
    reset_url = f"{host}api/auth/reset-password?token={token}"

    # Режим локальної симуляції (без затримок і без зовнішнього SMTP)
    if settings.mail_simulate:
        print(
            f"\n✉️  [MOCK EMAIL] Імітація надсилання листа для скидання пароля на адресу: {email}"
        )
        print(f"🔑 Одноразовий токен скидання: {token}")
        print(f"🔗 Посилання скидання: {reset_url}\n")
        return

    # Якщо симуляція вимкнена, але увімкнено показ посилання в логах
    if settings.debug_show_token_in_logs:
        print(f"\n🔗 [DEV RESET TOKEN URL]: {reset_url}")
        print(f"🔑 [DEV RESET TOKEN]: {token}\n")

    message = MessageSchema(
        subject="Скидання пароля до облікового запису",
        recipients=[email],
        template_body={
            "host": host,
            "username": username,
            "token": token,
            "reset_url": reset_url,
            "expires_minutes": settings.password_reset_token_expire_minutes,
        },
        subtype=MessageType.html,
    )
    try:
        await mailer.send_message(message, template_name="email/reset_password.html")
    except ConnectionErrors as err:
        logger.warning(
            "Не вдалося відправити лист скидання пароля на адресу %s (SMTP недоступний): %s",
            email,
            err,
        )
