#!/usr/bin/env python3
"""
Ethio Shoe Store - Telegram Bot (Render Deployment Ready)
Main entry point with Flask health check and webhook support
"""

import os
import sys
import threading
import time
import asyncio
import logging
from flask import Flask, jsonify
from telebot import TeleBot, custom_filters
from telebot.storage import StateMemoryStorage

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
# FLASK APPLICATION (For Render Health Checks)
# ============================================================

app = Flask(__name__)

@app.route('/')
def home():
    """Root endpoint - basic health check."""
    return jsonify({
        "status": "ok",
        "service": "Ethio Shoe Store Telegram Bot",
        "version": "2.0.0"
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
                bot.infinity_polling(timeout=10, long_polling_timeout=5)
            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(5)

    poll_thread = threading.Thread(target=poll, daemon=True)
    poll_thread.start()
    logger.info("✅ Polling mode activated")

# ============================================================
# SUPERVISION REAL-TIME ORDER MONITORING
# ============================================================

class OrderMonitor:
    """Monitor Supabase for new orders in real-time."""

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
        from datetime import datetime, timedelta

        # Initialize Supabase client
        supa_client = supabase.create_client(SUPABASE_URL, SUPABASE_KEY)

        # Track last check time
        last_check = datetime.utcnow()

        while self.running:
            try:
                # Query for new orders created after last check
                result = supa_client.table('orders')\
                    .select('*')\
                    .gte('created_at', last_check.isoformat())\
                    .execute()

                if result.data:
                    for order in result.data:
                        self._notify_new_order(order)

                last_check = datetime.utcnow()
                time.sleep(10)  # Check every 10 seconds

            except Exception as e:
                logger.error(f"Order monitoring error: {e}")
                time.sleep(30)

    def _notify_new_order(self, order):
        """Send notification for new order."""
        try:
            order_id = order.get('id', 'N/A')
            customer_name = order.get('customer_name', 'Customer')
            total_amount = order.get('total_amount', 0)
            phone = order.get('customer_phone', 'N/A')

            # Notify admins
            for admin_id in ADMIN_IDS:
                message = (
                    f"🔔 <b>New Order Received!</b>\n\n"
                    f"Order ID: <code>{order_id}</code>\n"
                    f"Customer: {customer_name}\n"
                    f"Phone: {phone}\n"
                    f"Total: {total_amount} ETB\n\n"
                    f"Status: ⏱️ Pending"
                )

                self.bot.send_message(
                    admin_id,
                    message,
                    parse_mode='HTML'
                )

            logger.info(f"📢 Notified admins of order {order_id}")

        except Exception as e:
            logger.error(f"Failed to notify order: {e}")

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

    # Wait for Flask to start
    time.sleep(2)

    # Start order monitoring
    order_monitor = OrderMonitor(bot)
    order_monitor.start()

    # Try webhook mode, fallback to polling
    if WEBHOOK_URL:
        if start_webhook_mode(bot):
            # Webhook is handled by Flask route
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
