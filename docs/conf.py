"""Конфігураційний файл для генератора документації Sphinx."""

import os
import sys

# Додавання кореня проєкту до sys.path для імпортування пакета src
sys.path.insert(0, os.path.abspath(".."))

# Загальна інформація про проєкт
project = "Contacts REST API"
copyright = "2026, GoIT Neoversity"
author = "FullStack Web Development Student"
release = "0.2.0"

# Підключені розширення Sphinx
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

# Локалізація інтерфейсу документації
language = "uk"

# Тема оформлення HTML
html_theme = "sphinx_rtd_theme"
html_static_path = []
# За потреби в масив можна додати "_static" якщо планується додавати в такий підкаталог кастомні стилі або зображення

# Налаштування розширення Napoleon (Google docstrings)
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False

# Налаштування розширення Autodoc
autodoc_member_order = "bysource"
autodoc_typehints = "description"

# Придушення попереджень про сторонні мітки SQLAlchemy у docstrings
suppress_warnings = ["ref.ref"]
