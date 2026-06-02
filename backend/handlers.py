# backend/handlers.py
"""
Bot handlers for Ethiopian Shoe Store
Updated to use PostgreSQL/Supabase backend
"""

import sys
import os
import logging
from datetime import datetime
from telebot import types

# Relative imports within backend package
from . import keyboards
from . import database as db

# Import config from parent directory
try:
    from config import ADMIN_IDS
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import ADMIN_IDS

logger = logging.getLogger(__name__)

# Temporary user state tracking for Checkout & Payments
USER_STATES = {}

def register_handlers(bot):

    # ============================================================
    # WELCOME / START COMMAND
    # ============================================================
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        chat_id = message.chat.id
        telegram_id = message.from_user.id
        first_name = message.from_user.first_name or "Customer"
        username = message.from_user.username

        try:
            db.db.create_user(telegram_id, first_name, username)
        except Exception as e:
            logger.error(f"Database error during user registration for {telegram_id}: {e}")

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

    # ============================================================
    # CART MANAGEMENT
    # ============================================================
    @bot.message_handler(commands=['cart'])
    def show_cart(message):
        chat_id = message.chat.id
        user = db.db.get_user(message.from_user.id)

        if not user:
            bot.send_message(chat_id, "⚠️ እባክዎ መጀመሪያ /start ይጫኑ።")
            return

        try:
            cart_items = db.db.get_cart_items(user['id'])
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

    # ============================================================
    # TEXT MESSAGE HANDLING (MAIN MENU)
    # ============================================================
    @bot.message_handler(func=lambda message: True)
    def handle_messages(message):
        chat_id = message.chat.id
        text = message.text.strip() if message.text else ""
        telegram_id = message.from_user.id

        # State machine processing for checkout / payments
        if telegram_id in USER_STATES:
            process_checkout_states(bot, message)
            return

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

        elif text == "🛒 ጋሪዬ":
            show_cart(message)

        elif text == "📞 እኛን ለማግኘት":
            bot.send_message(
                chat_id,
                "📞 እኛን ለማግኘት በስልክ ቁጥር +2519XXXXXXXX መደወል ይችላሉ።"
            )

        elif text == "🛍️ የእኔ ትዕዛዞች":
            user = db.db.get_user(telegram_id)
            if not user:
                bot.send_message(chat_id, "⚠️ እባክዎ መጀመሪያ /start ይጫኑ።")
                return

            try:
                orders = db.db.get_orders(user_id=user['id'])
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
                
                # If order is pending, allow adding payment details
                inline_markup = types.InlineKeyboardMarkup()
                if order.get('order_status') == 'pending':
                    inline_markup.add(types.InlineInlineKeyboardButton("💳 ክፍያ ፈጽም / መረጃ አስገባ", callback_data=f"pay_{order['id']}"))
                
                bot.send_message(chat_id, order_text, parse_mode="Markdown", reply_markup=inline_markup)

    # ============================================================
    # CALLBACK: CATEGORY SELECTION
    # ============================================================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"))
    def handle_category_selection(call):
        chat_id = call.message.chat.id
        category = call.data.split("_")[1] 
        bot.answer_callback_query(call.id)

        try:
            products = db.db.get_products_by_category(category)
        except Exception as e:
            logger.error(f"Failed to fetch products for {category}: {e}")
            bot.send_message(chat_id, "❌ መረጃዎችን ማግኘት አልተሳካም።")
            return

        if not products:
            bot.send_message(chat_id, f"⚠️ በአሁኑ ሰዓት በ '{category}' ምድብ ምንም ምርት የለም።")
            return

        for product in products[:11]:
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

    # ============================================================
    # CALLBACK: PRODUCT & VARIANT SELECTION
    # ============================================================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("product_"))
    def handle_product_detail(call):
        chat_id = call.message.chat.id
        product_id = call.data.replace("product_", "")
        bot.answer_callback_query(call.id)

        product = db.db.get_product(product_id)
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

        product = db.db.get_product(product_id)
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

        user = db.db.get_user(call.from_user.id)
        if not user:
            bot.send_message(chat_id, "⚠️ እባክዎ መጀመሪያ /start ይጫኑ።")
            return

        product = db.db.get_product(product_id)
        if not product:
            bot.send_message(chat_id, "⚠️ ምርቱ አልተገኘም።")
            return

        variants = product.get('product_variants', [])
        variant = next((v for v in variants if v['size'] == size and v['color'] == color), None)

        if not variant or variant.get('stock', 0) <= 0:
            bot.send_message(chat_id, "⚠️ ይህ ምርት አሁን በስቶክ ውስጥ የለም።")
            return

        try:
            cart_item = db.db.add_to_cart(user['id'], variant['id'], quantity=1)
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

    # ============================================================
    # CALLBACK: CLEAR CART
    # ============================================================
    @bot.callback_query_handler(func=lambda call: call.data == "clear_cart_action")
    def handle_clear_cart(call):
        chat_id = call.message.chat.id
        user = db.db.get_user(call.from_user.id)
        
        if user:
            db.db.clear_cart(user['id'])
            bot.answer_callback_query(call.id, "🗑️ ጋሪዎ በተሳካ ሁኔታ ጸድቷል!")
            bot.edit_message_text("🛒 ጋሪዎ ባዶ ተደርጓል፤ አዳዲስ ምርቶችን መምረጥ ይችላሉ።", chat_id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "⚠️ ስህተት ተከስቷል።")

    # ============================================================
    # CHECKOUT FLOW IMPLEMENTATION
    # ============================================================
    @bot.callback_query_handler(func=lambda call: call.data == "checkout")
    def start_checkout(call):
        chat_id = call.message.chat.id
        telegram_id = call.from_user.id
        bot.answer_callback_query(call.id)

        user = db.db.get_user(telegram_id)
        cart_items = db.db.get_cart_items(user['id'])

        if not cart_items:
            bot.send_message(chat_id, "⚠️ ቼክአውት ለማድረግ መጀመሪያ ጋሪዎ ውስጥ ምርት ይጨምሩ።")
            return

        # Start capturing shipping info
        USER_STATES[telegram_id] = {'step': 'get_city', 'cart_items': cart_items, 'user_uuid': user['id']}
        
        allowed_cities = ['Addis Ababa', 'Adama', 'Hawassa', 'Bahir Dar', 'Dire Dawa', 'Mekelle', 'Gondar', 'Jimma', 'Dessie', 'Shashamane']
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        for city in allowed_cities:
            markup.add(types.KeyboardButton(city))

        bot.send_message(chat_id, "📍 እባክዎ የሚረከቡበትን **ከተማ** ይምረጡ፦", reply_markup=markup, parse_mode="Markdown")

    def process_checkout_states(bot, message):
        telegram_id = message.from_user.id
        chat_id = message.chat.id
        text = message.text.strip() if message.text else ""
        state = USER_STATES.get(telegram_id)

        if state['step'] == 'get_city':
            allowed_cities = ['Addis Ababa', 'Adama', 'Hawassa', 'Bahir Dar', 'Dire Dawa', 'Mekelle', 'Gondar', 'Jimma', 'Dessie', 'Shashamane']
            if text not in allowed_cities:
                bot.send_message(chat_id, "⚠️ እባክዎ ከታች ካሉት ከተሞች ብቻ ይምረጡ።")
                return
            state['city'] = text
            state['step'] = 'get_subcity'
            bot.send_message(chat_id, "🏙️ እባክዎ **ክፍለ ከተማ ወይም ዞን** ያስገቡ፦", reply_markup=types.ReplyKeyboardRemove())

        elif state['step'] == 'get_subcity':
            state['subcity'] = text
            state['step'] = 'get_location'
            bot.send_message(chat_id, "📍 እባክዎ **ልዩ ቦታ ወይም ወረዳ** በግልጽ ያስገቡ፦")

        elif state['step'] == 'get_location':
            state['specific_location'] = text
            state['step'] = 'get_phone'
            bot.send_message(chat_id, "📞 እባክዎ ምርቱ ሲደርስ የሚደወልበትን **የስልክ ቁጥር** ያስገቡ፦")

        elif state['step'] == 'get_phone':
            state['phone'] = text
            
            # Save address to database
            address = db.db.add_address(
                user_id=state['user_uuid'],
                city=state['city'],
                subcity_or_zone=state['subcity'],
                specific_location=state['specific_location'],
                is_default=True
            )

            if not address:
                bot.send_message(chat_id, "❌ የአድራሻ መረጃ ማስቀመጥ አልተሳካም። እባክዎ እንደገና ይሞክሩ።")
                USER_STATES.pop(telegram_id, None)
                return

            # Calculate Order breakdown
            subtotal = 0
            order_items_payload = []
            
            for item in state['cart_items']:
                variant = item.get('product_variants', {})
                product = variant.get('products', {})
                qty = item.get('quantity', 1)
                price = product.get('base_price', 0)
                subtotal += (price * qty)

                order_items_payload.append({
                    'variant_id': variant.get('id'),
                    'product_name': product.get('name'),
                    'size': variant.get('size'),
                    'color': variant.get('color'),
                    'quantity': qty,
                    'price_per_unit': price
                })

            delivery_fee = 150 if state['city'] == 'Addis Ababa' else 250
            total_amount = subtotal + delivery_fee

            # Create Order in DB
            order = db.db.create_order(
                user_id=state['user_uuid'],
                items=order_items_payload,
                subtotal=subtotal,
                delivery_fee=delivery_fee,
                discount_amount=0,
                total_amount=total_amount,
                shipping_address_id=address['id'],
                contact_phone=state['phone']
            )

            if order:
                db.db.clear_cart(state['user_uuid'])
                order_id_short = str(order['id'])[:8]
                
                success_text = (
                    f"🎉 **ትዕዛዝዎ በተሳካ ሁኔታ ተመዝግቧል!**\n\n"
                    f"🆔 **የትዕዛዝ ቁጥር:** #{order_id_short}\n"
                    f"💵 **የምርት ዋጋ:** {subtotal} ETB\n"
                    f"🚚 **የማድረሻ ክፍያ:** {delivery_fee} ETB\n"
                    f"💰 **ጠቅላላ ድምር:** {total_amount} ETB\n\n"
                    f"👇 እባክዎ ከታች ያለውን የክፍያ ቁልፍ በመጫን ክፍያ ይፈጽሙ።"
                )
                
                inline_markup = types.InlineKeyboardMarkup()
                inline_markup.add(types.InlineKeyboardButton("💳 አሁን ክፍያ ፈጽም", callback_data=f"pay_{order['id']}"))
                
                bot.send_message(chat_id, success_text, parse_mode="Markdown", reply_markup=inline_markup)
            else:
                bot.send_message(chat_id, "❌ ትዕዛዝ መፍጠር አልተሳካም። እባክዎ እንደገና ይሞክሩ።")

            # Reset State
            USER_STATES.pop(telegram_id, None)
            send_welcome(message)

    # ============================================================
    # PAYMENT FLOW (CUSTOMER REGISTER TRANSACTION REFERENCE)
    # ============================================================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"))
    def handle_payment_start(call):
        chat_id = call.message.chat.id
        telegram_id = call.from_user.id
        order_id = call.data.replace("pay_", "")
        bot.answer_callback_query(call.id)

        USER_STATES[telegram_id] = {'step': 'get_payment_method', 'order_id': order_id}

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(types.KeyboardButton("telebirr"), types.KeyboardButton("cbe"))
        
        bot.send_message(
            chat_id, 
            "💳 እባክዎ የክፍያ ዘዴ ይምረጡ (የመረጡትን ይጫኑ)፦\n\n"
            "🔸 **telebirr**: ቁጥር `+2519XXXXXXXX`\n"
            "🔸 **CBE**: የሂሳብ ቁጥር `1000XXXXXXXXX`",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    @bot.message_handler(func=lambda m: USER_STATES.get(m.from_user.id, {}).get('step') in ['get_payment_method', 'get_tx_ref'])
    def process_payment_states(message):
        telegram_id = message.from_user.id
        chat_id = message.chat.id
        text = message.text.strip() if message.text else ""
        state = USER_STATES.get(telegram_id)

        if state['step'] == 'get_payment_method':
            if text not in ['telebirr', 'cbe']:
                bot.send_message(chat_id, "⚠️ እባክዎ ከታች ካሉት የክፍያ አማራጮች ብቻ ይምረጡ (telebirr ወይም cbe)።")
                return
            state['payment_method'] = text
            state['step'] = 'get_tx_ref'
            bot.send_message(chat_id, "✍️ እባክዎ የክፍያ ማረጋገጫ **የግብይት ቁጥር (Transaction Reference)** ያስገቡ፦", reply_markup=types.ReplyKeyboardRemove())

        elif state['step'] == 'get_tx_ref':
            payment = db.db.create_payment(
                order_id=state['order_id'],
                payment_method=state['payment_method'],
                transaction_reference=text
            )

            if payment:
                bot.send_message(chat_id, "✅ የክፍያ መረጃዎ ደርሶናል። አድሚን ሲያረጋግጠው ትዕዛዝዎ ይጸድቃል! እናመሰግናለን።")
            else:
                bot.send_message(chat_id, "❌ የክፍያ መረጃ መመዝገብ አልተሳካም። ትክክለኛ የግብይት ቁጥር ማስገባትዎን ያረጋግጡ።")

            USER_STATES.pop(telegram_id, None)
            send_welcome(message)

    # ============================================================
    # ADMIN PANEL: VIEW NEW ORDERS
    # ============================================================
    @bot.callback_query_handler(func=lambda call: call.data == "admin_view_orders")
    def admin_view_orders(call):
        telegram_id = call.from_user.id
        chat_id = call.message.chat.id

        if telegram_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, text="እርምጃው አልተፈቀደም!", show_alert=True)
            return

        bot.answer_callback_query(call.id)

        try:
            orders = db.db.get_orders(status='pending')
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
            order_id_short = str(order.get('id', ''))[:8]

            # Fetch payment record if any
            payment_info = db.db.get_payment_by_order(order['id'])
            pay_text = "⚠️ አልተከፈለም / መረጃ አልገባም"
            if payment_info:
                pay_text = f"💳 {payment_info['payment_method'].upper()} (Ref: `{payment_info['transaction_reference']}`)"

            order_text = (
                f"🆔 **ትዕዛዝ ID:** #{order_id_short}\n"
                f"👤 **ደንበኛ:** {user_name}\n"
                f"📞 **ስልክ:** {order.get('contact_phone', 'ያልተሰጠ')}\n"
                f"💰 **ጠቅላላ:** {order.get('total_amount', 0)} ETB\n"
                f"💵 **ክፍያ:** {pay_text}"
            )
            
            # Action to update order status or verify payment
            inline_markup = keyboards.get_order_status_keyboard(order['id'])
            if payment_info and not payment_info.get('is_verified'):
                inline_markup.add(types.InlineKeyboardButton("🔍 ክፍያ አረጋግጥ (Verify Payment)", callback_data=f"verify_pay_{payment_info['id']}"))

            bot.send_message(chat_id, order_text, parse_mode="Markdown", reply_markup=inline_markup)

    # ============================================================
    # ADMIN CALLBACKS: UPDATE ORDER STATUS & VERIFY PAYMENTS
    # ============================================================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("status_"))
    def admin_update_status(call):
        telegram_id = call.from_user.id
        chat_id = call.message.chat.id

        if telegram_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, text="እርምጃው አልተፈቀደም!", show_alert=True)
            return

        parts = call.data.split("_")
        order_id = parts[1]
        new_status = parts[2]

        if db.db.update_order_status(order_id, new_status):
            bot.answer_callback_query(call.id, text=f"የትዕዛዝ ሁኔታ ወደ '{new_status}' ተቀይሯል!")
            bot.edit_message_text(f"✅ የትዕዛዝ ቁጥር #{order_id[:8]} ሁኔታ በተሳካ ሁኔታ ወደ **{new_status.upper()}** ተቀይሯል።", chat_id, call.message.message_id, parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, text="⚠️ የትዕዛዝ ሁኔታን ማዘመን አልተሳካም።")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("verify_pay_"))
    def admin_verify_payment(call):
        telegram_id = call.from_user.id
        chat_id = call.message.chat.id

        if telegram_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, text="እርምጃው አልተፈቀደም!", show_alert=True)
            return

        payment_id = call.data.replace("verify_pay_", "")
        
        if db.db.verify_payment(payment_id, telegram_id):
            bot.answer_callback_query(call.id, text="💰 ክፍያው በተሳካ ሁኔታ ተረጋግጧል!")
            bot.edit_message_text("✅ ክፍያው ተረጋግጧል፤ ትዕዛዙም በራስ-ሰር ወደ **CONFIRMED** ተቀይሯል።", chat_id, call.message.message_id, parse_mode="Markdown")
        else:
            bot.answer_callback_query(call.id, text="❌ ክፍያ ማረጋገጥ አልተሳካም።")