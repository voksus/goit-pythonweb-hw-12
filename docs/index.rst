Документація проєкту Contacts REST API
======================================

Ласкаво просимо до офіційної документації асинхронного REST API застосунку контактної книги!

.. toctree::
   :maxdepth: 2
   :caption: Зміст документації:

Головний модуль застосунку
--------------------------
.. automodule:: src.main
   :members:
   :undoc-members:
   :show-inheritance:

Конфігурація та налаштування
----------------------------
.. automodule:: src.settings
   :members:
   :undoc-members:
   :show-inheritance:

Підключення до бази даних
-------------------------
.. automodule:: src.db
   :members:
   :undoc-members:
   :show-inheritance:

Залежності FastAPI
------------------
.. automodule:: src.dependencies
   :members:
   :undoc-members:
   :show-inheritance:

Моделі бази даних (SQLAlchemy)
------------------------------
.. automodule:: src.models
   :members:
   :undoc-members:
   :show-inheritance:

Схеми валідації даних (Pydantic)
--------------------------------
.. automodule:: src.schemas
   :members:
   :undoc-members:
   :show-inheritance:

Шар доступу до даних (Репозиторій)
----------------------------------
.. automodule:: src.repository
   :members:
   :undoc-members:
   :show-inheritance:

Маршрути API: Автентифікація (Auth)
-----------------------------------
.. automodule:: src.routers.auth
   :members:
   :undoc-members:
   :show-inheritance:

Маршрути API: Користувачі (Users)
---------------------------------
.. automodule:: src.routers.users
   :members:
   :undoc-members:
   :show-inheritance:

Маршрути API: Контакти (Contacts)
---------------------------------
.. automodule:: src.routers.contacts
   :members:
   :undoc-members:
   :show-inheritance:

Сервіс безпеки та автентифікації
--------------------------------
.. automodule:: src.services.security
   :members:
   :undoc-members:
   :show-inheritance:

Сервіс кешування (Redis)
------------------------
.. automodule:: src.services.cache
   :members:
   :undoc-members:
   :show-inheritance:

Сервіс електронної пошти
------------------------
.. automodule:: src.services.mail
   :members:
   :undoc-members:
   :show-inheritance:

Сервіс медіафайлів (Cloudinary)
-------------------------------
.. automodule:: src.services.upload_file
   :members:
   :undoc-members:
   :show-inheritance:

Покажчики та таблиці
====================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
