#!/usr/bin/env python3
"""
Ethio Shoe Store - Telegram Bot (Render Deployment Ready)
Main entry point with Flask health check, keep-alive ping, and webhook support
"""

import os
import sys
import threading
import time
import asyncio
import logging
import requests
from flask import Flask, jsonify
from telebot import TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
import telebot

# Import configuration (validates env vars on load)
from config import (
    BOT_TOKEN,
    ADMIN_IDS,
    SUPABASE_URL,
    SUPABASE_KEY,
    PORT,
    HOST,
    WEBHOOK_URL,
    LOG_LEVEL
)

# Import handlers
from backend.handlers import register_handlers
from backend.admin import register_admin_handlers
from backend.orders import register_order_handlers

# Configure logging
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================
# FLASK APPLICATION (For Render Health Checks & Keep-Alive)
# ============================================================

app = Flask(__name__)

@app.route('/')
def home():
    """Root endpoint - basic health check and keep alive target."""
    return jsonify({
        "status": "ok",
        "service": "Ethio Shoe Store Telegram Bot",
        "version": "2.0.0",
        "message": "Bot is Running Live!"
    })

@app.route('/health')
def health():
    """Health check endpoint for Render."""
    return jsonify({
        "status": "ok",
        "bot": "running",
        "timestamp": int(time.time())
    })

@app.route('/metrics')
def metrics():
    """Basic metrics endpoint."""
    return jsonify({
        "status": "ok",
        "admin_count": len(ADMIN_IDS)
    })

def run_flask():
    """Run Flask app for Render health checks."""
    try:
        logger.info(f"🌐 Starting Flask server on {HOST}:{PORT}")
        app.run(host=HOST, port=PORT, threaded=True)
    except Exception as e:
        logger.error(f"❌ Flask server error: {e}")
        sys.exit(1)

# ============================================================
# KEEP ALIVE LOGIC (እንዳይተኛ ራስን የመቀስቀሻ ሎጂክ)
# ============================================================

def keep_alive():
    """Background task to ping the server every 14 minutes to prevent Render spin-down."""
    # የዌብሁክ ሊንክ ካለ እሱን ይጠቀማል፣ ካልሆነ የተሰጠውን ዲፎልት ሊንክ ይወስዳል
    url = WEBHOOK_URL.split('/webhook')[0] if WEBHOOK_URL else "https://ethio-shoe-bot-v2.onrender.com"
    
    logger.info(f"⏰ Keep-alive monitor started targeting: {url}")
    time.sleep(30)  # ሰርቨሩ ሙሉ በሙሉ እስኪነሳ መጀመሪያ ትንሽ ይጠብቅ
    
    while True:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                logger.info("⏰ ሰርቨሩ እንዳይተኛ ራሱን ቀስቅሷል (Pinged Successfully)!")
            else:
                logger.warning(f"⏰ Keep-alive ping returned status code: {response.status_code}")
        except Exception as e:
            logger.error(f"⚠️ Ping ስህተት ገጥሟል፦ {e}")
            
        time.sleep(14 * 60)  # በየ 14 ደቂቃው (14 x 60 ሰከንድ) ይደጋገማል

# ============================================================
# TELEGRAM BOT INITIALIZATION
# ============================================================

def initialize_bot():
    """Initialize and configure the Telegram bot."""
    try:
        logger.info("🚀 Initializing Ethio Shoe Store Bot...")

        # Initialize bot with state storage
        state_storage = StateMemoryStorage()
        bot = TeleBot(BOT_TOKEN, state_storage=state_storage)

        # Remove existing webhooks
        bot.remove_webhook()
        time.sleep(0.5)

        # Add custom filters for state handling
        bot.add_custom_filter(custom_filters.StateFilter(bot))

        # Register all handlers
        logger.info("📦 Registering bot handlers...")
        register_admin_handlers(bot)
        register_order_handlers(bot)
        register_handlers(bot)

        logger.info("✅ Bot initialized successfully")
        return bot

    except Exception as e:
        logger.error(f"❌ Bot initialization failed: {e}")
        sys.exit(1)

# ============================================================
# WEBHOOK VS POLLING MODE
# ============================================================

def start_webhook_mode(bot):
    """Start bot in webhook mode (recommended for production)."""
    try:
        if not WEBHOOK_URL:
            logger.warning("⚠️ WEBHOOK_URL not set, falling back to polling")
            return False

        logger.info(f"🔗 Setting webhook: {WEBHOOK_URL}")

        # Set webhook
        bot.set_webhook(url=WEBHOOK_URL)

        # Start webhook listener
        from flask import request

        @app.route('/webhook', methods=['POST'])
        def webhook():
            if request.headers.get('content-type') == 'application/json':
                json_string = request.get_data().decode('utf-8')
                update = telebot.types.Update.de_json(json_string)
                bot.process_new_updates([update])
                return jsonify({"status": "ok"})
            return jsonify({"status": "error"}), 403

        logger.info("✅ Webhook mode activated")
        return True

    except Exception as e:
        logger.error(f"❌ Webhook mode failed: {e}")
        return False

def start_polling_mode(bot):
    """Start bot in polling mode (fallback)."""
    logger.info("🔄 Starting polling mode...")

    def poll():
        while True:
            try:
                bot.infinity_polling(timeout=20, long_polling_timeout=10)
            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(5)

    poll_thread = threading.Thread(target=poll, daemon=True)
    poll_thread.start()
    logger.info("✅ Polling mode activated")

# ============================================================
# SUPERVISION REAL-TIME ORDER MONITORING (ALIGNED WITH SCHEMA)
# ============================================================

class OrderMonitor:
    """Monitor Supabase for new orders in real-time with proper schema matching."""

    def __init__(self, bot):
        self.bot = bot
        self.running = False

    def start(self):
        """Start monitoring for new orders."""
        logger.info("📡 Starting order monitor...")
        self.running = True

        monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        monitor_thread.start()

    def _monitor_loop(self):
        """Background thread monitoring for new orders."""
        import supabase
        from datetime import datetime, timezone

        # Initialize Supabase client
        supa_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

        # Track last check time using ISO with UTC timezone to match Supabase TIMESTAMPTZ
        last_check = datetime.now(timezone.utc)

        while self.running:
            try:
                # Query public.orders and relationally join public.users to get the first_name
                result = supa_client.table('orders')\
                    .select('*, users(first_name)')\
                    .gte('created_at', last_check.isoformat())\
                    .execute()

                if result.data:
                    for order in result.data:
                        self._notify_new_order(order)

                last_check = datetime.now(timezone.utc)
                time.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"⚠️ Order monitoring query error: {e}")
                time.sleep(30)

    def _notify_new_order(self, order):
        """Send notification for new order matching exact public.orders DB structure."""
        try:
            order_id = order.get('id', 'N/A')
            total_amount = order.get('total_amount', 0)
            phone = order.get('contact_phone', 'N/A')
            status = order.get('order_status', 'pending')

            # Extract user first_name via relational join metadata
            user_data = order.get('users', {})
            customer_name = user_data.get('first_name', 'ያልታወቀ ደንበኛ') if user_data else 'ያልታወቀ ደንበኛ'

            # Notify admins
            for admin_id in ADMIN_IDS:
                message = (
                    f"🔔 <b>አዲስ ትዕዛዝ ደርሷል! (New Order)</b>\n\n"
                    f"<b>የማዘዣ ቁጥር (ID):</b> <code>{order_id}</code>\n"
                    f"<b>ደንበኛ:</b> {customer_name}\n"
                    f"<b>ስልክ ቁጥር:</b> {phone}\n"
                    f"<b>ጠቅላላ ዋጋ:</b> {total_amount} ETB\n"
                    f"<b>የሱቅ ሁኔታ (Status):</b> ⏱️ {status.capitalize()}"
                )

                self.bot.send_message(
                    admin_id,
                    message,
                    parse_mode='HTML'
                )

            logger.info(f"📢 Notified admins of order {order_id}")

        except Exception as e:
            logger.error(f"❌ Failed to parse or notify order: {e}")

# ============================================================
# MAIN ENTRY POINT
# ============================================================

def main():
    """Main entry point for the application."""
    logger.info("=" * 60)
    logger.info("🚀 Ethio Shoe Store Bot - Starting")
    logger.info("=" * 60)

    # Initialize bot
    bot = initialize_bot()

    # Start Flask server in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    logger.info("✅ Flask server started")

    # Start keep alive ping loop in background thread
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    logger.info("✅ Keep-alive loop thread started")

    # Wait for Flask to start
    time.sleep(2)

    # Start order monitoring
    order_monitor = OrderMonitor(bot)
    order_monitor.start()

    # Try webhook mode, fallback to polling
    if WEBHOOK_URL:
        if start_webhook_mode(bot):
            logger.info("✅ Running in webhook mode")
        else:
            start_polling_mode(bot)
    else:
        start_polling_mode(bot)

    logger.info("✅ Bot is running!")
    logger.info("=" * 60)

    # Keep main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutting down...")
        bot.remove_webhook()
        order_monitor.running = False
        sys.exit(0)

if __name__ == '__main__':
    main()