"""
Bot handlers for Ethiopian Shoe Store
Updated to use PostgreSQL/Supabase backend
"""

import sys
import os
import logging

# CRITICAL: Fix imports for Render deployment
# Use relative imports within backend package
from . import keyboards
from . import database as db

# Import config from parent directory
try:
    from config import ADMIN_IDS
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import ADMIN_IDS

logger = logging.getLogger(__name__)


def register_handlers(bot):

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        chat_id = message.chat.id
        telegram_id = message.from_user.id
        first_name = message.from_user.first_name or "Customer"
        username = message.from_user.username

        # Create or update user in database safely
        try:
            db.create_user(telegram_id, first_name, username)
        except Exception as e:
            logger.error(f"Database error during user registration for {telegram_id}: {e}")

        # Secure authorization: validate explicit telegram_id instead of chat_id
        if telegram_id in ADMIN_IDS:
            bot.send_message(
                chat_id,
                f"👨‍💼 ሰላም አድሚን {first_name}!",
                reply_markup=keyboards.get_admin_main_menu()
            )
        else:
            bot.send_message(
                chat_id,
                f"👋 እንኳን ወደ Ethio Shoe Store በደህና መጡ፣ {first_name}!",
                reply_markup=keyboards.get_main_menu()
            )

    @bot.message_handler(commands=['cart'])
    def show_cart(message):
        chat_id = message.chat.id
        user = db.get_user(message.from_user.id)

        if not user:
            bot.send_message(chat_id, "⚠️ እባክዎ መጀመሪያ /start ይጫኑ።")
            return

        try:
            cart_items = db.get_cart_items(user['id'])
        except Exception as e:
            logger.error(f"Cart acquisition transaction exception raised: {e}")
            bot.send_message(chat_id, "❌ የጋሪ መረጃዎችን ማምጣት አልተሳካም።")
            return

        if not cart_items:
            bot.send_message(chat_id, "🛒 ጋሪዎ ባዶ ነው።")
            return

        total = 0
        cart_text = "🛒 **የእርስዎ ጋሪ፦**\n\n"

        for item in cart_items:
            variant = item.get('product_variants', {})
            product = variant.get('products', {}) if variant else {}
            quantity = item.get('quantity', 1)
            price = product.get('base_price', 0) if product else 0
            subtotal = price * quantity
            total += subtotal

            if product:
                cart_text += (
                    f"👟 **{product.get('name', 'ጫማ')}**\n"
                    f"   📐 Size: {variant.get('size', 'N/A')}\n"
                    f"   🎨 Color: {variant.get('color', 'N/A')}\n"
                    f"   📦 Qty: {quantity}\n"
                    f"   💵 {subtotal} ETB (ብር)\n\n"
                )

        cart_text += f"💰 **ጠቅላላ: {total} ETB (ብር)**"

        bot.send_message(
            chat_id,
            cart_text,
            parse_mode="Markdown",
            reply_markup=keyboards.get_cart_checkout_keyboard()
        )

    @bot.message_handler(func=lambda message: True)
    def handle_messages(message):
        chat_id = message.chat.id
        text = message.text.strip() if message.text else ""
        telegram_id = message.from_user.id

        if text == "🔐 Admin Panel":
            if telegram_id in ADMIN_IDS:
                bot.send_message(
                    chat_id,
                    "🛠️ የአድሚን ማዘዣ ሰሌዳ፦",
                    reply_markup=keyboards.get_admin_panel_keyboard()
                )
            else:
                bot.send_message(chat_id, "⚠️ ይቅርታ፣ ይህ አልተፈቀደም።")

        elif text == "🔄 ወደ ዋና ማውጫ":
            reply_keyboard = keyboards.get_admin_main_menu() if telegram_id in ADMIN_IDS else keyboards.get_main_menu()
            bot.send_message(chat_id, "🏠 ወደ ዋና ማውጫ ተመልሰዋል።", reply_markup=reply_keyboard)

        elif text == "👟 ምርቶችን እይ":
            bot.send_message(
                chat_id,
                "🗂️ እባክህ የምትፈልገውን የምድብ አይነት ምረጥ፦",
                reply_markup=keyboards.get_category_menu()
            )

        elif text in ["👞 የወንዶች ጫማዎች", "👠 የሴቶች ጫማዎች", "👟 የህፃናት ጫማዎች", "👥 የሁለቱም"]:
            category_map = {
                "👞 የወንዶች ጫማዎች": "የወንዶች",
                "👠 የሴቶች ጫማዎች": "የሴቶች",
                "👟 የህፃናት ጫማዎች": "የህፃናት",
                "👥 የሁለቱም": "የሁለቱም"
            }
            category = category_map.get(text, "የወንዶች")

            try:
                products = db.get_products_by_category(category)
            except Exception as e:
                logger.error(f"Failed to fetch products for {category}: {e}")
                bot.send_message(chat_id, "❌ መረጃዎችን ከማውጫው ላይ ማግኘት አልተሳካም። እባክዎ ትንሽ ቆይተው ይሞክሩ።")
                return

            if not products:
                bot.send_message(chat_id, f"⚠️ በአሁኑ ሰዓት በ '{category}' ምድብ ስር ምንም ምርት የለም።")
                return

            for product in products[:10]:
                variants = product.get('product_variants', [])
                base_price = product.get('base_price', 0)
                original_price = product.get('original_price')

                price_display = f"💵 **ዋጋ፦** {base_price} ETB (ብር)"
                if original_price and original_price > base_price:
                    price_display = f"💵 **ዋጋ፦** ~~{original_price} ETB~~ **{base_price} ETB (ብር)**"

                variants_text = ""
                if variants:
                    sizes = sorted(set(v['size'] for v in variants if v.get('stock', 0) > 0))
                    colors = sorted(set(v['color'] for v in variants if v.get('stock', 0) > 0))
                    total_stock = sum(v.get('stock', 0) for v in variants)

                    if total_stock > 0:
                        variants_text = f"\n📐 **ያሉ ሳይዞች፦** {', '.join(map(str, sizes))}\n🎨 **ቀለሞች፦** {', '.join(colors)}\n📦 **በስቶክ ያለው፦** {total_stock} ጥንድ"
                    else:
                        variants_text = "\n❌ **ይህ ምርት በአሁኑ ሰዓት አልቋል (Out of Stock)**"

                caption = (
                    f"👟 **{product.get('name', 'ያልተገኘ ምርት')}**\n\n"
                    f"{price_display}"
                    f"{variants_text}\n\n"
                    f"📝 {product.get('description', 'ጥሩ ጥራት ያለው ጫማ')}"
                )

                image_url = None
                if variants and variants[0].get('image_url'):
                    image_url = variants[0]['image_url']

                inline_markup = keyboards.get_product_detail_keyboard(product['id'])

                if image_url:
                    try:
                        bot.send_photo(
                            chat_id,
                            image_url,
                            caption=caption,
                            parse_mode="Markdown",
                            reply_markup=inline_markup
                        )
                    except Exception as img_err:
                        logger.error(f"Image dispatch failed for product {product.get('id')}: {img_err}")
                        bot.send_message(chat_id, caption, parse_mode="Markdown", reply_markup=inline_markup)
                else:
                    bot.send_message(chat_id, caption, parse_mode="Markdown", reply_markup=inline_markup)

        elif text == "📞 እኛን ለማግኘት":
            bot.send_message(
                chat_id,
                "📞 እኛን ለማግኘት በስልክ ቁጥር +2519XXXXXXXX መደወል ይችላሉ።"
            )

        elif text == "🛍️ የእኔ ትዕዛዞች":
            user = db.get_user(telegram_id)
            if not user:
                bot.send_message(chat_id, "⚠️ እባክዎ መጀመሪያ /start ይጫኑ።")
                return

            try:
                orders = db.get_orders(user_id=user['id'])
            except Exception as e:
                logger.error(f"Error extracting tracking context for user {user['id']}: {e}")
                bot.send_message(chat_id, "❌ የትዕዛዝ መዝገቦችን ማምጣት አልተሳካም።")
                return

            if not orders:
                bot.send_message(chat_id, "📦 በአሁኑ ሰዓት ምንም አይነት ያላጠናቀቁት ትዕዛዝ የለም።")
                return

            bot.send_message(chat_id, "🛍️ **የእርስዎ የትዕዛዞች ዝርዝር፦**", parse_mode="Markdown")
            for order in orders:
                status_map = {
                    'pending': '⏱️ ይጠበቃል',
                    'confirmed': '✅ ተረጋግጧል',
                    'shipped': '🚚 ተልኳል',
                    'delivered': '📦 ተጠናቋል',
                    'cancelled': '❌ ተሰርዟል'
                }
                status_display = status_map.get(order.get('order_status'), "ያልታወቀ ሁኔታ")
                order_id_short = str(order.get('id', ''))[:8]

                order_text = (
                    f"🆔 **የትዕዛዝ ቁጥር:** #{order_id_short}\n"
                    f"💰 **ጠቅላላ ዋጋ:** {order.get('total_amount', 0)} ETB (ብር)\n"
                    f"🚦 **ሁኔታ:** {status_display}"
                )
                bot.send_message(chat_id, order_text, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("product_"))
    def handle_product_detail(call):
        chat_id = call.message.chat.id
        product_id = call.data.replace("product_", "")
        bot.answer_callback_query(call.id)

        product = db.get_product(product_id)
        if not product:
            bot.send_message(chat_id, "⚠️ ምርቱ አልተገኘም።")
            return

        variants = product.get('product_variants', [])
        if not variants:
            bot.send_message(chat_id, "⚠️ ምርቱ ለሽያጭ ዝግጁ አይደለም።")
            return

        available_sizes = sorted(set(v['size'] for v in variants if v.get('stock', 0) > 0))
        if not available_sizes:
            bot.send_message(chat_id, "⚠️ ምርቱ አሁን በስቶክ ውስጥ የለም።")
            return

        bot.send_message(
            chat_id,
            f"📐 ለ **{product.get('name', 'ጫማ')}** የሚፈልጉትን ሳይዝ ይምረጡ፦",
            parse_mode="Markdown",
            reply_markup=keyboards.get_size_selection_keyboard(product_id, available_sizes)
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("size_"))
    def handle_size_selection(call):
        chat_id = call.message.chat.id
        parts = call.data.split("_")
        
        if len(parts) < 3:
            bot.answer_callback_query(call.id, "⚠️ የተሳሳተ የመረጃ ቅርጸት ገብቷል።")
            return

        product_id = parts[1]
        try:
            size = int(parts[2])
        except ValueError:
            bot.answer_callback_query(call.id, "⚠️ የተሳሳተ ሳይዝ ተመርጧል።")
            return

        bot.answer_callback_query(call.id)

        product = db.get_product(product_id)
        if not product:
            bot.send_message(chat_id, "⚠️ ምርቱ አልተገኘም።")
            return

        variants = product.get('product_variants', [])
        matching_variants = [v for v in variants if v['size'] == size and v.get('stock', 0) > 0]

        if not matching_variants:
            bot.send_message(chat_id, f"⚠️ ሳይዝ {size} በስቶክ ውስጥ የለም።")
            return

        available_colors = [v['color'] for v in matching_variants]
        bot.send_message(
            chat_id,
            f"🎨 ለ ሳይዝ {size} የሚፈልጉትን ቀለም ይምረጡ፦",
            reply_markup=keyboards.get_color_selection_keyboard(product_id, size, available_colors)
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("color_"))
    def handle_color_selection(call):
        chat_id = call.message.chat.id
        parts = call.data.split("_")

        if len(parts) < 4:
            bot.answer_callback_query(call.id, "⚠️ የተሳሳተ የመረጃ ቅርጸት ገብቷል።")
            return

        product_id = parts[1]
        try:
            size = int(parts[2])
        except ValueError:
            bot.answer_callback_query(call.id, "⚠️ ስህተት ተከስቷል።")
            return

        color = "_".join(parts[3:])
        bot.answer_callback_query(call.id)

        user = db.get_user(call.from_user.id)
        if not user:
            bot.send_message(chat_id, "⚠️ እባክዎ መጀመሪያ /start ይጫኑ።")
            return

        product = db.get_product(product_id)
        if not product:
            bot.send_message(chat_id, "⚠️ ምርቱ አልተገኘም።")
            return

        variants = product.get('product_variants', [])
        variant = next((v for v in variants if v['size'] == size and v['color'] == color), None)

        if not variant or variant.get('stock', 0) <= 0:
            bot.send_message(chat_id, "⚠️ ይህ ምርት አሁን በስቶክ ውስጥ የለም።")
            return

        try:
            cart_item = db.add_to_cart(user['id'], variant['id'], quantity=1)
            if cart_item:
                bot.send_message(
                    chat_id,
                    f"✅ **{product.get('name', 'ምርት')}** ({size}, {color}) ወደ ጋሪዎ በተሳካ ሁኔታ ተጨምሯል!\n\n"
                    f"💵 ዋጋ: {product.get('base_price', 0)} ETB (ብር)\n\n"
                    f"🛒 ጋሪዎን ለማየት /cart ይጫኑ ወይም ሌሎች ምርቶችን ይመልከቱ።",
                    parse_mode="Markdown"
                )
            else:
                bot.send_message(chat_id, "⚠️ ወደ ጋሪ መጨመር አልተሳካም።")
        except Exception as e:
            logger.error(f"Failed handling cart transaction sequence: {e}")
            bot.send_message(chat_id, "❌ ምርቱን ወደ ጋሪ መጫን አልተሳካም።")

    @bot.callback_query_handler(func=lambda call: call.data == "clear_cart_action")
    def handle_clear_cart(call):
        chat_id = call.message.chat.id
        user = db.get_user(call.from_user.id)
        
        if user:
            db.clear_cart(user['id'])
            bot.answer_callback_query(call.id, "🗑️ ጋሪዎ በተሳካ ሁኔታ ጸድቷል!")
            bot.edit_message_text("🛒 ጋሪዎ ባዶ ተደርጓል፤ አዳዲስ ምርቶችን መምረጥ ይችላሉ።", chat_id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "⚠️ ስህተት ተከስቷል።")

    @bot.callback_query_handler(func=lambda call: call.data == "admin_view_orders")
    def admin_view_orders(call):
        telegram_id = call.from_user.id
        chat_id = call.message.chat.id

        if telegram_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, text="እርምጃው አልተፈቀደም!", show_alert=True)
            return

        bot.answer_callback_query(call.id)

        try:
            orders = db.get_orders(status='pending')
        except Exception as e:
            logger.error(f"Admin runtime error when scanning operations arrays: {e}")
            bot.send_message(chat_id, "❌ አዳዲስ ትዕዛዞችን ማምጣት አልተሳካም።")
            return

        if not orders:
            bot.send_message(chat_id, "📭 በአሁኑ ሰዓት ምንም አዲስ ትዕዛዝ የለም።")
            return

        bot.send_message(chat_id, "📦 **የገቡ አዳዲስ ትዕዛዞች ዝርዝር፦**", parse_mode="Markdown")
        for order in orders[:10]:
            user = order.get('users', {})
            user_name = user.get('first_name', 'Unknown') if user else 'Unknown'

            status_map = {
                'pending': '⏱️ ይጠበቃል',
                'confirmed': '✅ ተረጋግጧል',
                'shipped': '🚚 ተልኳል',
                'delivered': '📦 ተጠናቋል',
                'cancelled': '❌ ተሰርዟል'
            }
            status_display = status_map.get(order.get('order_status'), order.get('order_status', 'N/A'))
            order_id_short = str(order.get('id', ''))[:8]

            order_text = (
                f"🆔 **ትዕዛዝ ID:** #{order_id_short}\n"
                f"👤 **ደንበኛ:** {user_name}\n"
                f"📞 **ስልክ:** {order.get('contact_phone', 'ያልተሰጠ')}\n"
                f"💰 **ጠቅላላ:** {order.get('total_amount', 0)} ETB\n"
                f"🚦 **ሁኔታ:** {status_display}"
            )
            bot.send_message(chat_id, order_text, parse_mode="Markdown")