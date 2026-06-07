# backend/__init__.py
# Marks the backend directory as a Python package.
# Re-exports registration functions for bot.py to import cleanly.
# Does NOT create a second DatabaseManager — use db.db from database.py directly.

from .handlers import register_handlers
from .admin import register_admin_handlers
from .orders import register_order_handlers
from .database import supabase, DatabaseManager, db
from . import keyboards
from . import receipt

__all__ = [
    'register_handlers',
    'register_admin_handlers',
    'register_order_handlers',
    'db',
    'keyboards',
    'receipt',
    'supabase',
    'DatabaseManager',
]
