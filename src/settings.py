"""Налаштування застосунку, валідовані через pydantic-settings."""

from urllib.parse import quote_plus

from pydantic import EmailStr, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Конфігурація параметрів середовища застосунку.

    Завантажує налаштування з файлу .env та системних змінних середовища.
    Містить секції для БД, JWT, Redis, поштового сервера, Cloudinary та дебагу.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        str_strip_whitespace=True,
        extra="ignore",
    )

    app_title: str = "Contacts REST API"
    app_version: str = "0.2.0"
    app_description: str = (
        "REST API контактної книги з JWT-автентифікацією, ролями, верифікацією пошти, "
        "обмеженням запитів slowapi, Redis-кешуванням та Cloudinary."
    )

    # База даних
    db_user: str = "postgres"
    db_password: SecretStr = SecretStr("mysecretpassword")
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "hw12_db"

    # JWT
    secret_key: SecretStr = SecretStr("supersecretjwtkey_must_be_set_in_env")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 1
    verification_token_expire_minutes: int = 1440  # 24 години
    password_reset_token_expire_minutes: int = 15

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: SecretStr | None = None
    redis_cache_expire_minutes: int = 2

    # Поштовий сервер (FastAPI-Mail через Mailpit)
    mail_username: str = "example@meta.ua"
    mail_password: SecretStr = SecretStr("secret_mail_password")
    mail_from: EmailStr = "example@meta.ua"
    mail_from_name: str = "Contacts REST API"
    mail_port: int = 1025
    mail_server: str = "localhost"
    mail_starttls: bool = False
    mail_ssl_tls: bool = False
    mail_use_credentials: bool = False
    mail_validate_certs: bool = False

    # Cloudinary
    cloudinary_name: str = "your_cloud_name"
    cloudinary_api_key: str = "your_api_key"
    cloudinary_api_secret: SecretStr = SecretStr("your_api_secret")

    # Дебаг
    debug_mode_enabled: bool = False
    debug_show_token_in_logs: bool = False
    mail_simulate: bool = False

    @computed_field
    @property
    def database_url(self) -> str:
        """Динамічне формування безпечного асинхронного URL підключення до PostgreSQL.

        Returns:
            str: Екранований рядок з'єднання для драйвера psycopg3.
        """
        password = quote_plus(self.db_password.get_secret_value())
        return (
            f"postgresql+psycopg://{self.db_user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


settings = Settings()
