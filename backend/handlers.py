"""
Main bot handlers for Ethio Shoe Store.
Handles /start, category browsing, product display, cart, and order history.
Production-grade with proper error handling and state management.
"""
import sys
import os
import logging
from telebot import types

from . import keyboards
from . import database as db

try:
    from config import ADMIN_IDS
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import ADMIN_IDS

logger = logging.getLogger(__name__)

# Category display mapping: DB value -> User-facing Amharic label
CATEGORY_LABELS = {
    'የወንዶች': 'የወንዶች (Men)',
    'የሴቶች': 'የሴቶች (Women)',
    'የህፃናት': 'የህፃናት (Kids)',
    'የሁለቱም/Unisex': 'ለሁሉም (Unisex)',
}


def register_handlers(bot):

    # ---------------------------------------------------------------- /start

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        chat_id     = message.chat.id
        telegram_id = message.from_user.id
        first_name  = message.from_user.first_name or "Customer"
        username    = message.from_user.username

        try:
            db.db.create_user(telegram_id, first_name, username)
        except Exception as e:
            logger.error(f"create_user error for {telegram_id}: {e}")

        if telegram_id in ADMIN_IDS:
            bot.send_message(chat_id, f"👨‍💼 ሰላም አድሚን {first_name}! ወደ አድሚን ፓነል በደህና መጡ።",
                             reply_markup=keyboards.get_admin_main_menu())
        else:
            bot.send_message(chat_id,
                             f"👋 እንኳን ወደ Ethio Shoe Store በደህና መጡ፣ {first_name}! ጥሩ ጫማዎችን ለማግኘት ያማረንን ምርት ይመልከቱ።",
                             reply_markup=keyboards.get_main_menu())

    # ---------------------------------------------------------------- /cart

    @bot.message_handler(commands=['cart'])
    def show_cart_cmd(message):
        _show_cart(bot, message.chat.id, message.from_user.id)

    # ---------------------------------------------------------------- main menu handler

    @bot.message_handler(content_types=['text'], func=lambda message: True, state=None)
    def handle_text(message):
        chat_id     = message.chat.id
        telegram_id = message.from_user.id
        text        = message.text.strip()

        if text == "🔐 አድሚን ፓነል":
            if telegram_id in ADMIN_IDS:
                bot.send_message(chat_id, "🛠️ አድሚን ፓነል፦",
                                 reply_markup=keyboards.get_admin_panel_keyboard())
            else:
                bot.send_message(chat_id, "⚠️ ይቅርታ፣ ይህ ተግባር አልተፈቀደም።")

        elif text == "🔄 ወደ ዋና መመለሻ":
            mk = keyboards.get_admin_main_menu() if telegram_id in ADMIN_IDS else keyboards.get_main_menu()
            bot.send_message(chat_id, "🏠 ወደ ዋና መምሪያ ተመልሰዋል።", reply_markup=mk)

        elif text == "👟 ጫማዎችን ይመልከቱ":
            bot.send_message(chat_id, "🗂️ ምድቡን ይምረጡ፦",
                             reply_markup=keyboards.get_category_menu())

        elif text == "🛒 የኔ ጋሪ":
            _show_cart(bot, chat_id, telegram_id)

        elif text == "📞 አግኙን":
            bot.send_message(chat_id,
                "📞 ስልክ: +251938649925\n⏰ ሰ-ሐ 8:00–20:00 | ሐሙ 10:00–18:00")

        elif text == "🛍️ ትዕዛዞቼ":
            _show_my_orders(bot, chat_id, telegram_id)

        else:
            mk = keyboards.get_admin_main_menu() if telegram_id in ADMIN_IDS else keyboards.get_main_menu()
            bot.send_message(chat_id, "🏠 ከዚህ ካሉት አዝራሮች ይምረጡ፦", reply_markup=mk)

    # ---------------------------------------------------------------- helpers

    def _show_cart(bot, chat_id, telegram_id):
        user = db.db.get_user(telegram_id)
        if not user:
            bot.send_message(chat_id, "⚠️ /start ን ይጫኑ።")
            return

        cart_items = db.db.get_cart_items(user['id'])
        if not cart_items:
            bot.send_message(chat_id, "🛒 ጋሪዎ ባዶ ነው።")
            return

        total     = 0
        cart_text = "🛒 <b>የእርስዎ ጋሪ፦</b>\n\n"

        for item in cart_items:
            variant = item.get('product_variants') or {}
            if isinstance(variant, list):
                variant = variant[0] if variant else {}
            product = variant.get('products') or {}
            if isinstance(product, list):
                product = product[0] if product else {}

            qty      = int(item.get('quantity', 1))
            price    = int(product.get('base_price', 0)) if product else 0
            subtotal = price * qty
            total   += subtotal

            if product:
                cart_text += (
                    f"👟 <b>{product.get('name', 'ጫማ')}</b>\n"
                    f"   📐 Size: {variant.get('size', 'N/A')}\n"
                    f"   🎨 Color: {variant.get('color', 'N/A')}\n"
                    f"   📦 Qty: {qty} | 💵 {subtotal} ETB\n\n"
                )

        cart_text += f"💰 <b>ጠቅላላ: {total} ETB</b>"
        bot.send_message(chat_id, cart_text, parse_mode="HTML",
                         reply_markup=keyboards.get_cart_checkout_keyboard())

    def _show_my_orders(bot, chat_id, telegram_id):
        user = db.db.get_user(telegram_id)
        if not user:
            bot.send_message(chat_id, "⚠️ /start ን ይጫኑ።")
            return

        orders = db.db.get_orders(user_id=user['id'])
        if not orders:
            bot.send_message(chat_id, "📦 ምንም ትዕዛዝ አልተገኘም።")
            return

        STATUS_MAP = {
            'pending':   '⏱️ በመጠባበቅ ላይ',
            'confirmed': '✅ ተረጋግጧል',
            'shipped':   '🚚 ተልኳል',
            'delivered': '📦 ተጠናቋል',
            'cancelled': '❌ ተሰርዟል',
        }

        bot.send_message(chat_id, "🛍️ <b>የእርስዎ ትዕዛዞች፦</b>", parse_mode="HTML")
        for order in orders:
            status   = STATUS_MAP.get(order.get('order_status', 'pending'), 'ያልታወቀ')
            short_id = str(order.get('id', ''))[:8]
            order_text = (
                f"🆔 <b>#{short_id}</b>\n"
                f"💰 {order.get('total_amount', 0)} ETB\n"
                f"🚦 {status}"
            )
            markup = types.InlineKeyboardMarkup()
            payment = order.get('payments')
            # Check for pending payment
            if payment and isinstance(payment, list) and len(payment) > 0:
                pay = payment[0]
                if pay.get('is_verified') is False and order.get('order_status') == 'pending':
                    markup.add(types.InlineKeyboardButton(
                        "💳 ክፍያ Reference አስገባ",
                        callback_data=f"pending_pay_{order['id']}"
                    ))
            elif order.get('order_status') == 'pending':
                markup.add(types.InlineKeyboardButton(
                    "💳 ክፍያ Reference አስገባ",
                    callback_data=f"pending_pay_{order['id']}"
                ))
            bot.send_message(chat_id, order_text, parse_mode="HTML", reply_markup=markup)

    # ---------------------------------------------------------------- category callbacks

    @bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
    def handle_category_selection(call):
        chat_id  = call.message.chat.id
        category = call.data.replace("cat_", "", 1)
        bot.answer_callback_query(call.id)

        try:
            products = db.db.get_products_by_category(category)
        except Exception as e:
            logger.error(f"get_products_by_category error: {e}")
            bot.send_message(chat_id, "❌ ምርቶችን ለማምጣት ስህተት ተከስቷል።")
            return

        label = CATEGORY_LABELS.get(category, category)
        if not products:
            bot.send_message(chat_id,
                f"⚠️ '<b>{label}</b>' ምድብ ውስጥ ምርት አልተገኘም።", parse_mode="HTML")
            return

        bot.send_message(chat_id, f"📂 <b>{label}</b> ምርቶች፦", parse_mode="HTML")
        for product in products[:10]:
            try:
                _send_product_card(bot, chat_id, product)
            except Exception as e:
                logger.error(f"Error sending product card for {product.get('id')}: {e}")

    def _send_product_card(bot, chat_id, product):
        variants      = product.get('product_variants') or []
        available     = [v for v in variants if int(v.get('stock', 0)) >= 1]
        base_price    = int(product.get('base_price', 0))
        original_price = product.get('original_price')
        total_stock   = sum(int(v.get('stock', 0)) for v in variants)

        price_line = f"💵 {base_price} ETB"
        if original_price and int(original_price) > base_price:
            price_line = f"💵 <s>{original_price}</s> <b>{base_price} ETB</b>"

        # Check if completely out of stock
        is_out_of_stock = total_stock <= 0 or len(available) == 0

        if is_out_of_stock:
            stock_line = "❌ ይህ ጫማ በአሁኑ ሰዓት አልቋል"
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

        # Only show "Add to Cart" button if product has stock
        if is_out_of_stock:
            markup = types.InlineKeyboardMarkup()  # Empty markup - no buttons
            caption += "\n\n⚠️ <i>ለጊዜው የለም - ቆይተው ይሞክሩ</i>"
        else:
            markup = keyboards.get_product_detail_keyboard(product['id'])

        sent = False
        if available:
            lead = available[0]
            # Try Telegram file_id first (fastest)
            if lead.get('telegram_file_id'):
                try:
                    bot.send_photo(chat_id, lead['telegram_file_id'],
                                   caption=caption, parse_mode="HTML", reply_markup=markup)
                    sent = True
                except Exception as e:
                    logger.warning(f"file_id send failed: {e}")
            # Fallback to URL
            if not sent and lead.get('image_url'):
                try:
                    bot.send_photo(chat_id, lead['image_url'],
                                   caption=caption, parse_mode="HTML", reply_markup=markup)
                    sent = True
                except Exception as e:
                    logger.warning(f"URL photo send failed: {e}")
        # If no stock or couldn't send photo, try the first variant that has an image
        elif not sent:
            for v in variants:
                if v.get('telegram_file_id'):
                    try:
                        bot.send_photo(chat_id, v['telegram_file_id'],
                                       caption=caption, parse_mode="HTML", reply_markup=markup)
                        sent = True
                        break
                    except Exception:
                        continue
                if v.get('image_url'):
                    try:
                        bot.send_photo(chat_id, v['image_url'],
                                       caption=caption, parse_mode="HTML", reply_markup=markup)
                        sent = True
                        break
                    except Exception:
                        continue

        if not sent:
            bot.send_message(chat_id, caption, parse_mode="HTML", reply_markup=markup)

    # ---------------------------------------------------------------- product -> size -> color -> cart

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

        # IMPORTANT: Do not allow size selection if out of stock
        if not available:
            bot.send_message(chat_id,
                "⚠️ ይህ ጫማ በአሁኑ ሰዓት አልቋል።\n\n"
                "እባክዎ ቆይተው ይሞክሩ ወይም ሌሎች ምርቶችን ይመልከቱ።")
            return

        sizes = sorted(set(int(v['size']) for v in available))
        bot.send_message(chat_id,
            f"📐 <b>{product.get('name')}</b> — Size ይምረጡ፦",
            parse_mode="HTML",
            reply_markup=keyboards.get_size_selection_keyboard(product_id, sizes))

    @bot.callback_query_handler(func=lambda call: call.data.startswith("size_"))
    def handle_size_selection(call):
        chat_id = call.message.chat.id
        parts   = call.data.split("_")
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

        variants = product.get('product_variants') or []
        matching = [v for v in variants if int(v['size']) == size and int(v.get('stock', 0)) >= 1]
        if not matching:
            bot.send_message(chat_id, f"⚠️ Size {size} አሁን የለም።")
            return

        colors = sorted(set(v['color'] for v in matching))
        bot.send_message(chat_id, f"🎨 Size {size} — ቀለም ይምረጡ፦",
                         reply_markup=keyboards.get_color_selection_keyboard(product_id, size, colors))

    @bot.callback_query_handler(func=lambda call: call.data.startswith("color_"))
    def handle_color_selection(call):
        chat_id     = call.message.chat.id
        telegram_id = call.from_user.id
        parts       = call.data.split("_")
        if len(parts) < 4:
            bot.answer_callback_query(call.id, "⚠️ ስህተት።")
            return
        product_id = parts[1]
        try:
            size = int(parts[2])
        except ValueError:
            bot.answer_callback_query(call.id, "⚠️ ስህተት።")
            return
        color = "_".join(parts[3:])
        bot.answer_callback_query(call.id)

        user = db.db.get_user(telegram_id)
        if not user:
            bot.send_message(chat_id, "⚠️ /start ን ይጫኑ።")
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
            bot.send_message(chat_id,
                f"✅ <b>{product.get('name')}</b> (Size {size}, {color}) ወደ ጋሪ ተጨምሯል!\n\n"
                f"💵 {int(product.get('base_price', 0))} ETB\n\n"
                f"🛒 ጋሪ ለማየት /cart ን ይጫኑ ወይም 🛒 የኔ ጋሪ ን ይጫኑ።",
                parse_mode="HTML")
        else:
            bot.send_message(chat_id, "❌ ወደ ጋሪ ማከል አልተሳካም።")

    # ---------------------------------------------------------------- cart actions

    @bot.callback_query_handler(func=lambda call: call.data == "clear_cart_action")
    def handle_clear_cart(call):
        chat_id     = call.message.chat.id
        telegram_id = call.from_user.id
        bot.answer_callback_query(call.id)

        user = db.db.get_user(telegram_id)
        if not user:
            bot.send_message(chat_id, "⚠️ ስህተት ተከስቷል።")
            return
        db.db.clear_cart(user['id'])
        bot.send_message(chat_id, "🗑️ ጋሪዎ ተጸድቷል።")
