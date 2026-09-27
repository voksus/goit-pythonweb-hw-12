"""Пакет застосунку. Дозволяє запускати: uvicorn src:app --reload"""

from .main import app

__all__ = ["app"]
