# backend/__init__.py
# This file marks the backend directory as a Python package
# and exports all necessary functions for easy importing from parent

# Import all handler registration functions from submodules
from .handlers import register_handlers
from .admin import register_admin_handlers
from .orders import register_order_handlers
from .database import supabase, DatabaseManager
from . import keyboards
from . import receipt

# Initialize database manager instance
db = DatabaseManager()

# Export all functions and modules
__all__ = [
    'register_handlers',
    'register_admin_handlers',
    'register_order_handlers',
    'db',
    'keyboards',
    'receipt',
    'supabase',
    'DatabaseManager'
]
