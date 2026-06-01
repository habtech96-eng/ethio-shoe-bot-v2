# config.py - Ethio Shoe Store Configuration
# SECURE: All credentials loaded from environment variables

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Bot Configuration
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN not found in environment variables. Please set it in Render.")

# Admin Configuration
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_IDS', '7098279917').split(',') if id.strip().isdigit()]

# Supabase Configuration
SUPABASE_URL = os.getenv('SUPABASE_URL') or os.getenv('VITE_SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY') or os.getenv('VITE_SUPABASE_ANON_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("❌ SUPABASE_URL and SUPABASE_KEY must be set in environment variables.")

# Flask/Render Configuration
PORT = int(os.getenv('PORT', 10000))
HOST = os.getenv('HOST', '0.0.0.0')

# Bot Settings
BOT_NAME = "Ethio Shoe Store Bot"
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '')
WEBHOOK_PATH = os.getenv('WEBHOOK_PATH', '/webhook')

# Logging
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

# Validate critical configuration
def validate_config():
    """Validate all required configuration is present."""
    errors = []

    if not BOT_TOKEN:
        errors.append("BOT_TOKEN is missing")

    if not SUPABASE_URL:
        errors.append("SUPABASE_URL is missing")

    if not SUPABASE_KEY:
        errors.append("SUPABASE_KEY is missing")

    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")

    return True

# Call validation on import (fail fast)
try:
    validate_config()
    print("✅ Configuration validated successfully")
except ValueError as e:
    print(f"⚠️ Configuration validation failed: {e}")
