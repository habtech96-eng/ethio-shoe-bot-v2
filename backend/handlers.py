"""
Main bot handlers for Ethio Shoe Store.
Handles /start, category browsing, product display, cart, and order history.
"""
import sys
import os
import logging
from datetime import datetime
from telebot import types

from . import keyboards
from . import database as db

try:
    from config import ADMIN_IDS
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import ADMIN_IDS

logger = logging.getLogger(__name__)


def register_handlers(bot):

    # ---------------------------------------------------------------- /start

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        chat_id    = message.chat.id
        telegram_id = message.from_user.id
        first_name  = message.from_user.first_name or "Customer"
        username    = message.from_user.username

        try:
            db.db.create_user(telegram_id, first_name, username)
        except Exception as e:
            logger.error(f"create_user error for {telegram_id}: {e}")

        if telegram_id in ADMIN_IDS:
            bot.send_message(chat_id, f"👨‍💼 ሰላም አድሚን {first_name}!",
                             reply_markup=keyboards.get_admin_main_menu())
        else:
            bot.send_message(chat_id,
                             f"👋 እንኳን ወደ Ethio Shoe Store በደህና መጡ፣ {first_name}!",
                             reply_markup=keyboards.get_main_menu())

    # ---------------------------------------------------------------- /cart

    @bot.message_handler(commands=['cart'])
    def show_cart_cmd(message):
        _show_cart(bot, message.chat.id, message.from_user.id)

    # ---------------------------------------------------------------- text menu

    @bot.message_handler(func=lambda message: True)
    def handle_text(message):
        chat_id     = message.chat.id
        telegram_id = message.from_user.id
        text        = message.text.strip() if message.text else ""

        if text == "🔐 Admin Panel":
            if telegram_id in ADMIN_IDS:
                bot.send_message(chat_id, "🛠️ Admin Panel፦",
                                 reply_markup=keyboards.get_admin_panel_keyboard())
            else:
                bot.send_message(chat_id, "⚠️ ይቅርታ፣ ይህ አልተፈቀደም።")

        elif text == "🔄 ወደ ዋና ማውጫ":
            mk = keyboards.get_admin_main_menu() if telegram_id in ADMIN_IDS else keyboards.get_main_menu()
            bot.send_message(chat_id, "🏠 ወደ ዋና ማውጫ ተመልሰዋል።", reply_markup=mk)

        elif text == "👟 ምርቶችን እይ":
            bot.send_message(chat_id, "🗂️ ምድቡን ይምረጡ፦",
                             reply_markup=keyboards.get_category_menu())

        elif text == "🛒 ጋሪዬ":
            _show_cart(bot, chat_id, telegram_id)

        elif text == "📞 እኛን ለማግኘት":
            bot.send_message(chat_id,
                "📞 ስልክ: +251938649925\n⏰ ሰ-ሐ 8:00–20:00 | ሐሙ 10:00–18:00")

        elif text == "🛍️ የእኔ ትዕዛዞች":
            _show_my_orders(bot, chat_id, telegram_id)

    # ---------------------------------------------------------------- helpers

    def _show_cart(bot, chat_id, telegram_id):
        user = db.db.get_user(telegram_id)
        if not user:
            bot.send_message(chat_id, "⚠️ /start ን ጫኑ።")
            return

        cart_items = db.db.get_cart_items(user['id'])
        if not cart_items:
            bot.send_message(chat_id, "🛒 ጋሪዎ ባዶ ነው።")
            return

        total = 0
        text  = "🛒 <b>የእርስዎ ጋሪ፦</b>\n\n"

        for item in cart_items:
            variant = item.get('product_variants') or {}
            if isinstance(variant, list):
                variant = variant[0] if variant else {}
            product = variant.get('products') or {}
            if isinstance(product, list):
                product = product[0] if product else {}

            qty      = int(item.get('quantity', 1))
            price    = int(product.get('base_price', 0))
            subtotal = price * qty
            total   += subtotal

            if product:
                text += (
                    f"👟 <b>{product.get('name', 'ጫማ')}</b>\n"
                    f"   📐 Size: {variant.get('size', 'N/A')}\n"
                    f"   🎨 Color: {variant.get('color', 'N/A')}\n"
                    f"   📦 Qty: {qty} | 💵 {subtotal} ETB\n\n"
                )

        text += f"💰 <b>ጠቅላላ: {total} ETB</b>"

        bot.send_message(chat_id, text, parse_mode="HTML",
                         reply_markup=keyboards.get_cart_checkout_keyboard())

    def _show_my_orders(bot, chat_id, telegram_id):
        user = db.db.get_user(telegram_id)
        if not user:
            bot.send_message(chat_id, "⚠️ /start ን ጫኑ።")
            return

        orders = db.db.get_orders(user_id=user['id'])
        if not orders:
            bot.send_message(chat_id, "📦 ምንም ትዕዛዝ አልተገኘም።")
            return

        STATUS_MAP = {
            'pending':   '⏱️ ይጠበቃል',
            'confirmed': '✅ ተረጋግጧል',
            'shipped':   '🚚 ተልኳል',
            'delivered': '📦 ደርሷል',
            'cancelled': '❌ ተሰርዟል',
        }

        bot.send_message(chat_id, "🛍️ <b>የእርስዎ ትዕዛዞች፦</b>", parse_mode="HTML")
        for order in orders:
            status  = STATUS_MAP.get(order.get('order_status', 'pending'), 'ያልታወቀ')
            short_id = str(order.get('id', ''))[:8]

            order_text = (
                f"🆔 <b>#{short_id}</b>\n"
                f"💰 {order.get('total_amount', 0)} ETB\n"
                f"🚦 {status}"
            )

            # Show "Pay now" button for pending orders that have no verified payment
            markup = types.InlineKeyboardMarkup()
            if order.get('order_status') == 'pending':
                markup.add(types.InlineKeyboardButton(
                    "💳 ክፍያ Reference ያስገቡ",
                    callback_data=f"pending_pay_{order['id']}"
                ))

            bot.send_message(chat_id, order_text, parse_mode="HTML", reply_markup=markup)

    # ---------------------------------------------------------------- category callbacks

    @bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
    def handle_category_selection(call):
        chat_id = call.message.chat.id
        # Safely extract category: "cat_የወንዶች" → "የወንዶች"
        # Use replace once to handle categories that contain underscores
        category = call.data.replace("cat_", "", 1)
        bot.answer_callback_query(call.id)

        try:
            products = db.db.get_products_by_category(category)
        except Exception as e:
            logger.error(f"get_products_by_category error: {e}")
            bot.send_message(chat_id, "❌ ምርቶችን ለማምጣት ስህተት ተከስቷል።")
            return

        if not products:
            bot.send_message(chat_id, f"⚠️ '<b>{category}</b>' ምድብ ውስጥ ምርት አልተገኘም።",
                             parse_mode="HTML")
            return

        for product in products[:10]:
            try:
                _send_product_card(bot, chat_id, product)
            except Exception as e:
                logger.error(f"Error sending product card for {product.get('id')}: {e}")

    def _send_product_card(bot, chat_id, product):
        variants          = product.get('product_variants') or []
        available         = [v for v in variants if int(v.get('stock', 0)) >= 1]

        base_price     = int(product.get('base_price', 0))
        original_price = product.get('original_price')
        price_line     = f"💵 {base_price} ETB"
        if original_price and int(original_price) > base_price:
            price_line = f"💵 <s>{original_price}</s> <b>{base_price} ETB</b>"

        if not available:
            stock_line = "❌ Out of Stock"
        else:
            sizes  = sorted(set(int(v['size'])  for v in available))
            colors = sorted(set(v['color']       for v in available))
            total  = sum(int(v.get('stock', 0))  for v in available)
            stock_line = (
                f"📐 Sizes: {', '.join(map(str, sizes))}\n"
                f"🎨 Colors: {', '.join(colors)}\n"
                f"📦 {total} ጥንድ"
            )

        caption = (
            f"👟 <b>{product.get('name', 'ምርት')}</b>\n\n"
            f"{price_line}\n"
            f"{stock_line}\n\n"
            f"📝 {product.get('description', 'ጥሩ ጥራት ያለው ጫማ')}"
        )
        markup = keyboards.get_product_detail_keyboard(product['id'])

        # Prefer Telegram file_id > URL > text-only
        sent = False
        if available:
            lead_variant = available[0]

            # 1. Try Telegram file_id (instant, free of bandwidth)
            if lead_variant.get('telegram_file_id'):
                try:
                    bot.send_photo(chat_id, lead_variant['telegram_file_id'],
                                   caption=caption, parse_mode="HTML", reply_markup=markup)
                    sent = True
                except Exception as e:
                    logger.warning(f"file_id send failed, falling back to URL: {e}")

            # 2. Fallback to URL
            if not sent and lead_variant.get('image_url'):
                try:
                    bot.send_photo(chat_id, lead_variant['image_url'],
                                   caption=caption, parse_mode="HTML", reply_markup=markup)
                    sent = True
                except Exception as e:
                    logger.warning(f"URL photo send failed: {e}")

        if not sent:
            bot.send_message(chat_id, caption, parse_mode="HTML", reply_markup=markup)

    # ---------------------------------------------------------------- product → size → color → cart

    @bot.callback_query_handler(func=lambda call: call.data.startswith("product_"))
    def handle_product_selection(call):
        chat_id    = call.message.chat.id
        product_id = call.data.replace("product_", "", 1)
        bot.answer_callback_query(call.id)

        product = db.db.get_product(product_id)
        if not product:
            bot.send_message(chat_id, "⚠️ ምርቱ አልተገኘም።")
            return

        variants  = product.get('product_variants') or []
        available = [v for v in variants if int(v.get('stock', 0)) >= 1]
        if not available:
            bot.send_message(chat_id, "⚠️ ምርቱ አሁን Out of Stock ነው።")
            return

        sizes = sorted(set(int(v['size']) for v in available))
        bot.send_message(
            chat_id,
            f"📐 <b>{product.get('name')}</b> — Size ይምረጡ፦",
            parse_mode="HTML",
            reply_markup=keyboards.get_size_selection_keyboard(product_id, sizes)
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("size_"))
    def handle_size_selection(call):
        chat_id = call.message.chat.id
        parts   = call.data.split("_")  # ["size", product_id, size_value]
        if len(parts) < 3:
            bot.answer_callback_query(call.id, "⚠️ ስህተት።")
            return

        product_id = parts[1]
        try:
            size = int(parts[2])
        except ValueError:
            bot.answer_callback_query(call.id, "⚠️ ስህተት።")
            return

        bot.answer_callback_query(call.id)
        product = db.db.get_product(product_id)
        if not product:
            bot.send_message(chat_id, "⚠️ ምርቱ አልተገኘም።")
            return

        variants  = product.get('product_variants') or []
        matching  = [v for v in variants if int(v['size']) == size and int(v.get('stock', 0)) >= 1]
        if not matching:
            bot.send_message(chat_id, f"⚠️ Size {size} አሁን የለም።")
            return

        colors = sorted(set(v['color'] for v in matching))
        bot.send_message(
            chat_id,
            f"🎨 Size {size} — ቀለም ይምረጡ፦",
            reply_markup=keyboards.get_color_selection_keyboard(product_id, size, colors)
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("color_"))
    def handle_color_selection(call):
        chat_id    = call.message.chat.id
        telegram_id = call.from_user.id
        parts       = call.data.split("_")  # ["color", product_id, size, color...]

        if len(parts) < 4:
            bot.answer_callback_query(call.id, "⚠️ ስህተት።")
            return

        product_id = parts[1]
        try:
            size = int(parts[2])
        except ValueError:
            bot.answer_callback_query(call.id, "⚠️ ስህተት።")
            return
        color = "_".join(parts[3:])  # support multi-word colors
        bot.answer_callback_query(call.id)

        user = db.db.get_user(telegram_id)
        if not user:
            bot.send_message(chat_id, "⚠️ /start ን ጫኑ።")
            return

        product = db.db.get_product(product_id)
        if not product:
            bot.send_message(chat_id, "⚠️ ምርቱ አልተገኘም።")
            return

        variants = product.get('product_variants') or []
        variant  = next(
            (v for v in variants
             if int(v['size']) == size and v['color'] == color and int(v.get('stock', 0)) >= 1),
            None
        )
        if not variant:
            bot.send_message(chat_id, "⚠️ ምርቱ አሁን የለም።")
            return

        result = db.db.add_to_cart(user['id'], variant['id'], quantity=1)
        if result:
            bot.send_message(
                chat_id,
                f"✅ <b>{product.get('name')}</b> (Size {size}, {color}) ጋሪዎ ላይ ተጨምሯል!\n\n"
                f"💵 {int(product.get('base_price', 0))} ETB\n\n"
                f"🛒 ጋሪ ለማየት /cart ይጫኑ ወይም ሌሎች ምርቶችን ይምረጡ።",
                parse_mode="HTML"
            )
        else:
            bot.send_message(chat_id, "❌ ጋሪ ላይ ማከል አልተሳካም።")

    # ---------------------------------------------------------------- cart actions

    @bot.callback_query_handler(func=lambda call: call.data == "clear_cart_action")
    def handle_clear_cart(call):
        chat_id    = call.message.chat.id
        telegram_id = call.from_user.id
        bot.answer_callback_query(call.id)

        user = db.db.get_user(telegram_id)
        if not user:
            bot.send_message(chat_id, "⚠️ ስህተት ተከስቷል።")
            return

        db.db.clear_cart(user['id'])
        bot.send_message(chat_id, "🗑️ ጋሪዎ ጸዳ።")
