"""
Bot handlers for Ethiopian Shoe Store
Updated to use PostgreSQL/Supabase backend
"""
from config import ADMIN_IDS
import keyboards
from backend.database import db


def register_handlers(bot):

    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        chat_id = message.chat.id
        telegram_id = message.from_user.id
        first_name = message.from_user.first_name
        username = message.from_user.username

        # Create or update user in database
        user = db.create_user(telegram_id, first_name, username)

        if chat_id in ADMIN_IDS:
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

    @bot.message_handler(func=lambda message: True)
    def handle_messages(message):
        chat_id = message.chat.id
        text = message.text.strip()
        telegram_id = message.from_user.id

        if text == "🔐 Admin Panel":
            if chat_id in ADMIN_IDS:
                bot.send_message(
                    chat_id,
                    "🛠️ የአድሚን ማዘዣ ሰሌዳ፦",
                    reply_markup=keyboards.get_admin_panel_keyboard()
                )
            else:
                bot.send_message(chat_id, "⚠️ ይቅርታ፣ ይህ አልተፈቀደም።")

        elif text == "🔄 ወደ ዋና ማውጫ":
            reply_keyboard = keyboards.get_admin_main_menu() if chat_id in ADMIN_IDS else keyboards.get_main_menu()
            bot.send_message(chat_id, "🏠 ወደ ዋና ማውጫ ተመልሰዋል።", reply_markup=reply_keyboard)

        elif text == "👟 ምርቶችን እይ":
            bot.send_message(
                chat_id,
                "🗂️ እባክህ የምትፈልገውን የምድብ አይነት ምረጥ፦",
                reply_markup=keyboards.get_category_menu()
            )

        elif text in ["👞 የወንዶች ጫማዎች", "👠 የሴቶች ጫማዎች", "👟 የህፃናት ጫማዎች", "👥 የሁለቱም/Unisex"]:
            # Map text to category
            category_map = {
                "👞 የወንዶች ጫማዎች": "የወንዶች",
                "👠 የሴቶች ጫማዎች": "የሴቶች",
                "👟 የህፃናት ጫማዎች": "የህፃናት",
                "👥 የሁለቱም/Unisex": "የሁለቱም/Unisex"
            }
            category = category_map.get(text, "የወንዶች")

            # Get products from PostgreSQL
            products = db.get_products_by_category(category)

            if not products:
                bot.send_message(chat_id, f"⚠️ በአሁኑ ሰዓት በ '{category}' ምድብ ስር ምንም ምርት የለም።")
                return

            # Display products with variants
            for product in products:
                variants = product.get('product_variants', [])

                # Format price with ETB
                base_price = product['base_price']
                original_price = product.get('original_price')

                price_display = f"💵 **ዋጋ፦** {base_price} ETB (ብር)"
                if original_price and original_price > base_price:
                    price_display = f"💵 **ዋጋ፦** ~~{original_price} ETB~~ **{base_price} ETB (ብር)**"

                # Format variants
                variants_text = ""
                if variants:
                    sizes = sorted(set(v['size'] for v in variants if v.get('stock', 0) > 0))
                    colors = sorted(set(v['color'] for v in variants if v.get('stock', 0) > 0))
                    total_stock = sum(v.get('stock', 0) for v in variants)

                    variants_text = f"\n📐 **ያሉ ሳይዞች፦** {', '.join(map(str, sizes))}\n🎨 **ቀለሞች፦** {', '.join(colors)}\n📦 **በስቶክ ያለው፦** {total_stock} ጥንድ"

                caption = (
                    f"👟 **{product['name']}**\n\n"
                    f"{price_display}"
                    f"{variants_text}\n\n"
                    f"📝 {product.get('description', 'ጥሩ ጥራት ያለ ጫማ')}"
                )

                # Get first variant image if available
                image_url = None
                if variants and variants[0].get('image_url'):
                    image_url = variants[0]['image_url']

                # Send message with inline keyboard for ordering
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
                    except:
                        bot.send_message(
                            chat_id,
                            caption,
                            parse_mode="Markdown",
                            reply_markup=inline_markup
                        )
                else:
                    bot.send_message(
                        chat_id,
                        caption,
                        parse_mode="Markdown",
                        reply_markup=inline_markup
                    )

        elif text == "📞 እኛን ለማግኘት":
            bot.send_message(
                chat_id,
                "📞 እኛን ለማግኘት በስልክ ቁጥር +2519XXXXXXXX መደወል ይችላሉ።"
            )

        elif text == "🛍️ የእኔ ትዕዛዞች":
            # Get user from database
            user = db.get_user(telegram_id)
            if not user:
                bot.send_message(chat_id, "⚠️ እባክዎ መጀመሪያ /start ይጫኑ።")
                return

            # Get user orders from PostgreSQL
            orders = db.get_orders(user_id=user['id'])

            if not orders:
                bot.send_message(chat_id, "📦 በአሁኑ ሰዓት ምንም አይነት ያላጠናቀቁት ትዕዛዝ የለም።")
                return

            bot.send_message(chat_id, "🛍️ **የእርስዎ የትዕዛዞች ዝርዝር፦**", parse_mode="Markdown")
            for order in orders:
                # Translate status to Amharic
                status_map = {
                    'pending': '⏱️ ይጠበቃል',
                    'confirmed': '✅ ተረጋግጧል',
                    'shipped': '🚚 ተልኳል',
                    'delivered': '📦 ተልኳል / ተጠናቋል',
                    'cancelled': '❌ ተሰርዟል'
                }
                status_display = status_map.get(order['order_status'], order['order_status'])

                order_text = (
                    f"🆔 **የትዕዛዝ ቁጥር:** #{order['id'][:8]}\n"
                    f"💰 **ጠቅላላ ዋጋ:** {order['total_amount']} ETB (ብር)\n"
                    f"🚦 **ሁኔታ:** {status_display}"
                )
                bot.send_message(chat_id, order_text, parse_mode="Markdown")

    # 🛍️ Inline button handlers
    @bot.callback_query_handler(func=lambda call: call.data.startswith("product_"))
    def handle_product_detail(call):
        chat_id = call.message.chat.id
        product_id = call.data.replace("product_", "")
        bot.answer_callback_query(call.id)

        # Get product details
        product = db.get_product(product_id)
        if not product:
            bot.send_message(chat_id, "⚠️ ምርቱ አልተገኘም።")
            return

        variants = product.get('product_variants', [])
        if not variants:
            bot.send_message(chat_id, "⚠️ ምርቱ ለሽያጭ ዝግጁ አይደለም።")
            return

        # Send size selection
        available_sizes = sorted(set(v['size'] for v in variants if v.get('stock', 0) > 0))
        if not available_sizes:
            bot.send_message(chat_id, "⚠️ ምርቱ አሁን በስቶክ ውስጥ የለም።")
            return

        bot.send_message(
            chat_id,
            f"📐 ለ **{product['name']}** የሚፈልጉትን ሳይዝ ይምረጡ፦",
            parse_mode="Markdown",
            reply_markup=keyboards.get_size_selection_keyboard(product_id, available_sizes)
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("size_"))
    def handle_size_selection(call):
        chat_id = call.message.chat.id
        parts = call.data.split("_")
        product_id = parts[1]
        size = int(parts[2])
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

        # Send color selection
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
        product_id = parts[1]
        size = int(parts[2])
        color = "_".join(parts[3:])  # In case color has underscores
        bot.answer_callback_query(call.id)

        # Get user
        user = db.get_user(call.from_user.id)
        if not user:
            bot.send_message(chat_id, "⚠️ እባክዎ መጀመሪያ /start ይጫኑ።")
            return

        # Get variant with matching size and color
        product = db.get_product(product_id)
        variants = product.get('product_variants', [])
        variant = next((v for v in variants if v['size'] == size and v['color'] == color), None)

        if not variant or variant.get('stock', 0) <= 0:
            bot.send_message(chat_id, "⚠️ ይህ ምርት አሁን በስቶክ ውስጥ የለም።")
            return

        # Add to cart
        cart_item = db.add_to_cart(user['id'], variant['id'], quantity=1)

        if cart_item:
            bot.send_message(
                chat_id,
                f"✅ **{product['name']}** ({size}, {color}) ወደ ጋሪዎ ታች ተጨምሯል!\n\n"
                f"💵 ዋጋ: {product['base_price']} ETB (ብር)\n\n"
                f"🛒 ዘንድ ለመሄድ /cart ይጫኑ ወይም ሌሎች ምርቶችን ይመልከቱ።",
                parse_mode="Markdown"
            )
        else:
            bot.send_message(chat_id, "⚠️ ወደ ጋሪ መጨመር አልተሳካም።")

    # Cart commands
    @bot.message_handler(commands=['cart'])
    def show_cart(message):
        chat_id = message.chat.id
        user = db.get_user(message.from_user.id)

        if not user:
            bot.send_message(chat_id, "⚠️ እባክዎ መጀመሪያ /start ይጫኑ።")
            return

        cart_items = db.get_cart_items(user['id'])

        if not cart_items:
            bot.send_message(chat_id, "🛒 ጋሪዎ ባዶ ነው።")
            return

        total = 0
        cart_text = "🛒 **የእርስዎ ጋሪ፦**\n\n"

        for item in cart_items:
            variant = item['product_variants']
            product = variant['products']
            quantity = item['quantity']
            price = product['base_price']
            subtotal = price * quantity
            total += subtotal

            cart_text += (
                f"👟 **{product['name']}**\n"
                f"   📐 Size: {variant['size']}\n"
                f"   🎨 Color: {variant['color']}\n"
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

    # Admin view orders
    @bot.callback_query_handler(func=lambda call: call.data == "admin_view_orders")
    def admin_view_orders(call):
        chat_id = call.message.chat.id
        if chat_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, text="እርምጃው አልተፈቀደም!", show_alert=True)
            return

        bot.answer_callback_query(call.id)
        orders = db.get_orders(status='pending')

        if not orders:
            bot.send_message(chat_id, "📭 በአሁኑ ሰዓት ምንም አዲስ ትዕዛዝ የለም።")
            return

        bot.send_message(chat_id, "📦 **የገቡ አዳዲስ ትዕዛዞች ዝርዝር፦**", parse_mode="Markdown")
        for order in orders[:10]:  # Show first 10
            user = order.get('users', {})
            user_name = user.get('first_name', 'Unknown') if user else 'Unknown'

            status_map = {
                'pending': '⏱️ ይጠበቃል',
                'confirmed': '✅ ተረጋግጧል',
                'shipped': '🚚 ተልኳል',
                'delivered': '📦 ተጠናቋል',
                'cancelled': '❌ ተሰርዟል'
            }
            status_display = status_map.get(order['order_status'], order['order_status'])

            order_text = (
                f"🆔 **ትዕዛዝ ID:** #{order['id'][:8]}\n"
                f"👤 **ደንበኛ:** {user_name}\n"
                f"📞 **ስልክ:** {order['contact_phone']}\n"
                f"💰 **ጠቅላላ:** {order['total_amount']} ETB\n"
                f"🚦 **ሁኔታ:** {status_display}"
            )
            bot.send_message(chat_id, order_text, parse_mode="Markdown")
