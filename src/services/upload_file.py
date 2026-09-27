"""Сервіс завантаження та трансформації медіафайлів через Cloudinary."""

from __future__ import annotations

import cloudinary
import cloudinary.uploader
from fastapi import UploadFile

from ..settings import settings


class UploadFileService:
    """Інкапсуляція взаємодії з Cloudinary API для завантаження та кадрування зображень."""

    def __init__(self) -> None:
        """Ініціалізація клієнта Cloudinary з параметрами із налаштувань."""
        cloudinary.config(
            cloud_name=settings.cloudinary_name,
            api_key=settings.cloudinary_api_key,
            api_secret=settings.cloudinary_api_secret.get_secret_value(),
            secure=True,
        )

    @staticmethod
    def upload_file(file: UploadFile, username: str) -> str:
        """Завантажує файл у папку RestApp/<username> та повертає квадратний трансформований URL.

        Виконує автоматичне масштабування зображення до розміру 250x250 пікселів
        із заповненням (crop="fill").

        Args:
            file: Об'єкт завантаженого файлу з FastAPI.
            username: Ім'я користувача для структурування папок у сховищі.

        Returns:
            str: Публічний URL оптимізованого зображення у Cloudinary.
        """
        public_id = f"RestApp/{username}"
        response = cloudinary.uploader.upload(
            file.file,
            public_id=public_id,
            overwrite=True,
        )
        src_url: str = cloudinary.CloudinaryImage(public_id).build_url(
            width=250,
            height=250,
            crop="fill",
            version=response.get("version"),
        )
        return src_url
