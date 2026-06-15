"""
Admin handlers for Ethio Shoe Store.
Manages product/variant creation with Telegram file_id capture for fast photo delivery.
All field values strictly satisfy schema CHECK constraints.
State management uses (chat_id) as the key — valid for private chats (user_id == chat_id).
"""
import sys
import os
import re
import logging
from telebot.handler_backends import State, StatesGroup
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

from . import database as db

try:
    from config import ADMIN_IDS
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import ADMIN_IDS

logger = logging.getLogger(__name__)

# Prevent duplicate DB submissions when an admin submits rapidly
processing_admins = set()


# ----------------------------------------------------------------------
# INPUT SANITIZATION - Prevent injection attacks
# ----------------------------------------------------------------------

# Dangerous patterns to reject
DANGEROUS_PATTERNS = [
    r'ssh\s+',              # SSH commands
    r'scp\s+',              # SCP commands
    r'sudo\s+',             # Sudo commands
    r'root@',               # Root user references
    r'rm\s+-',              # rm commands
    r'wget\s+',             # wget downloads
    r'curl\s+',             # curl requests
    r'nc\s+-',              # netcat
    r'bash\s+-',           # bash execution
    r'/bin/',               # binary paths
    r'chmod\s+',            # chmod
    r'chown\s+',            # chown
    r'\|\s*sh',             # pipe to shell
    r'&&\s*\w',             # command chaining
    r';\s*\w',              # semicolon command separation
    r'SELECT\s+',           # SQL injection (case insensitive)
    r'INSERT\s+',
    r'UPDATE\s+',
    r'DELETE\s+',
    r'DROP\s+',
    r'UNION\s+',
    r'--\s*$',              # SQL comments
]

DANGEROUS_CHARS = ['<', '>', '{', '}', '`', '$', ';', '|', '&']


def sanitize_input(text, max_length=100, allow_amharic=True):
    """
    Validate and sanitize user input to prevent injection attacks.

    Returns: (sanitized_text, is_valid, error_message)
    """
    if not text:
        return None, False, "እባክዎ ዋጋ ያስገቡ።"

    text = text.strip()

    if len(text) > max_length:
        return None, False, f"ጽሑፍ በጣም ረጅም ነው (ከ{max_length} ፊደላት በታች)።"

    if not text or text.lower() == 'none' or text.lower() == 'null':
        return None, False, "እባክዘ ትክክለኛ ዋጋ ያስገቡ።"

    # Check for dangerous characters
    for char in DANGEROUS_CHARS:
        if char in text:
            return None, False, f"የማይፈቀድ ባህሪ: '{char}'"

    # Check for dangerous patterns (case insensitive)
    text_lower = text.lower()
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            logger.warning(f"Blocked dangerous input pattern: {pattern} in text: {text[:50]}")
            return None, False, "የማይፈቀድ ጽሑፍ ተገኝቷል። እባክዎ ሌላ ይሞክሩ።"

    # Check for URLs in non-URL fields
    if 'http://' in text_lower or 'https://' in text_lower:
        return None, False, "URL እዚህ ላይ አይፈቀድም።"

    # Check for email-like patterns
    if '@' in text and '.' in text and not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', text):
        return None, False, "የማይፈቀድ ኢሜል ቅርጸት።"

    return text, True, None


def sanitize_url(url):
    """
    Validate URL input specifically for image URLs.

    Returns: (sanitized_url, is_valid, error_message)
    """
    if not url:
        return None, True, None  # URLs are optional

    url = url.strip()

    # Must start with http:// or https://
    if not url.lower().startswith(('http://', 'https://')):
        return None, False, "URL በ http:// ወይም https:// መጀመር አለበት።"

    # Check for dangerous patterns in URL
    url_lower = url.lower()
    dangerous_url_patterns = ['javascript:', 'data:', 'file:', 'ftp:', 'ssh://']
    for pattern in dangerous_url_patterns:
        if pattern in url_lower:
            return None, False, "የማይፈቀድ URL ቅርጸት።"

    # Basic URL structure validation
    try:
        parsed = re.match(r'^https?://[\w\.-]+(?:\.[a-z]{2,})(?:/[^\s]*)?$', url, re.IGNORECASE)
        if not parsed:
            return None, False, "የማይፈቀድ URL ቅርጸት።"
    except:
        return None, False, "URL ማረጋገጥ አልተቻለም።"

    return url, True, None


class AddProductStates(StatesGroup):
    waiting_for_name           = State()
    waiting_for_category       = State()
    waiting_for_brand          = State()
    waiting_for_price          = State()
    waiting_for_original_price = State()
    waiting_for_description    = State()
    waiting_for_variant_size   = State()
    waiting_for_variant_color  = State()
    waiting_for_variant_stock  = State()
    waiting_for_variant_image  = State()


class AddVariantStates(StatesGroup):
    waiting_for_size  = State()
    waiting_for_color = State()
    waiting_for_stock = State()
    waiting_for_image = State()


def _category_markup():
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton("👞 የወንዶች (Men)",      callback_data="admin_cat_የወንዶች"),
        InlineKeyboardButton("👠 የሴቶች (Women)",    callback_data="admin_cat_የሴቶች"),
        InlineKeyboardButton("👟 የህፃናት (Kids)",    callback_data="admin_cat_የህፃናት"),
        InlineKeyboardButton("👥 ለሁሉም (Unisex)",  callback_data="admin_cat_የሁለቱም/Unisex"),
    )
    return m


def _brand_markup():
    m = InlineKeyboardMarkup(row_width=2)
    m.add(
        InlineKeyboardButton("Nike",             callback_data="admin_brand_Nike"),
        InlineKeyboardButton("Adidas",           callback_data="admin_brand_Adidas"),
        InlineKeyboardButton("Puma",             callback_data="admin_brand_Puma"),
        InlineKeyboardButton("Reebok",           callback_data="admin_brand_Reebok"),
        InlineKeyboardButton("Jordan",           callback_data="admin_brand_Jordan"),
        InlineKeyboardButton("ሀገር በቀል (Local)", callback_data="admin_brand_Local"),
        InlineKeyboardButton("ሌላ (Other)",        callback_data="admin_brand_Other"),
    )
    return m


def register_admin_handlers(bot):

    # ---------------------------------------------------------------- admin panel callbacks

    @bot.callback_query_handler(func=lambda call: call.data == "admin_add_product")
    def start_add_product(call):
        chat_id = call.message.chat.id
        if call.from_user.id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ ይህ ተግባር ለእርስዎ አልተፈቀደም!", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        bot.delete_state(call.from_user.id, chat_id)
        processing_admins.discard(chat_id)
        bot.set_state(call.from_user.id, AddProductStates.waiting_for_name, chat_id)
        bot.send_message(chat_id, "👟 እባክዎ የጫማውን ሙሉ ስም ያስገቡ (ምሳሌ፦ Nike Air Jordan 4)፦")

    @bot.callback_query_handler(func=lambda call: call.data == "admin_view_orders")
    def view_orders(call):
        if call.from_user.id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ አልተፈቀደም!", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        chat_id = call.message.chat.id

        orders = db.db.get_all_orders(status='pending', limit=20)
        if not orders:
            bot.send_message(chat_id, "📭 አሁን ምንም አዲስ ትዕዛዝ የለም።")
            return

        bot.send_message(chat_id, f"📦 <b>{len(orders)} አዳዲስ ትዕዛዞች:</b>", parse_mode="HTML")
        for order in orders:
            user_info  = order.get('users') or {}
            first_name = user_info.get('first_name', 'N/A') if isinstance(user_info, dict) else 'N/A'
            phone      = order.get('contact_phone', 'N/A')
            short_id   = str(order.get('id', ''))[:8]
            total      = order.get('total_amount', 0)
            text = (
                f"🆔 <b>#{short_id}</b>\n"
                f"👤 {first_name} | 📞 {phone}\n"
                f"💰 {total} ETB\n"
                f"🚦 {order.get('order_status', 'pending')}"
            )
            from . import keyboards
            bot.send_message(chat_id, text, parse_mode="HTML",
                             reply_markup=keyboards.get_order_status_keyboard(order['id']))

    @bot.callback_query_handler(func=lambda call: call.data == "admin_reports")
    def admin_reports(call):
        if call.from_user.id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ አልተፈቀደም!", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        orders = db.db.get_all_orders(limit=100)
        total_orders  = len(orders)
        total_revenue = sum(o.get('total_amount', 0) for o in orders)
        confirmed     = sum(1 for o in orders if o.get('order_status') == 'confirmed')
        pending       = sum(1 for o in orders if o.get('order_status') == 'pending')
        bot.send_message(
            call.message.chat.id,
            f"📊 <b>Reports</b>\n\n"
            f"📦 ጠቅላላ ትዕዛዞች: {total_orders}\n"
            f"✅ ተረጋግጠዋል: {confirmed}\n"
            f"⏱️ ይጠበቃሉ: {pending}\n"
            f"💰 ጠቅላላ ሽያጭ: {total_revenue} ETB",
            parse_mode="HTML"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("status_"))
    def handle_order_status_update(call):
        if call.from_user.id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ አልተፈቀደም!", show_alert=True)
            return
        parts = call.data.split("_")
        if len(parts) < 3:
            bot.answer_callback_query(call.id)
            return
        order_id   = parts[1]
        new_status = parts[2]
        bot.answer_callback_query(call.id)

        if db.db.update_order_status(order_id, new_status):
            bot.edit_message_text(
                f"✅ ትዕዛዝ #{order_id[:8]} ወደ <b>{new_status}</b> ተቀይሯል።",
                call.message.chat.id, call.message.message_id, parse_mode="HTML"
            )
            order = db.db.get_order(order_id)
            if order:
                user_data = order.get('users') or {}
                tg_id = user_data.get('telegram_id') if isinstance(user_data, dict) else None
                if tg_id:
                    labels = {
                        'confirmed': '✅ ተረጋግጧል',
                        'shipped':   '🚚 ተልኳል',
                        'delivered': '📦 ደርሷል',
                        'cancelled': '❌ ተሰርዟል',
                    }
                    try:
                        bot.send_message(tg_id,
                            f"🔔 ትዕዛዝ <b>#{order_id[:8]}</b>: {labels.get(new_status, new_status)}",
                            parse_mode="HTML")
                    except Exception:
                        pass
        else:
            bot.answer_callback_query(call.id, "❌ ሁኔታ ማስተካከል አልተሳካም።", show_alert=True)

    # ---------------------------------------------------------------- step 1: product name

    @bot.message_handler(state=AddProductStates.waiting_for_name)
    def process_name(message):
        chat_id = message.chat.id
        raw_name = message.text.strip() if message.text else ""

        # Validate and sanitize the product name
        name, is_valid, error_msg = sanitize_input(raw_name, max_length=100)
        if not is_valid:
            bot.send_message(chat_id, f"⚠️ {error_msg}")
            return

        # Additional product name checks
        if name.isdigit():
            bot.send_message(chat_id, "⚠️ የምርት ስም ቁጥር ብቻ መሆን አይችልም። እባክዎ ሙሉ ስም ያስገቡ።")
            return

        if name.startswith('/'):
            bot.send_message(chat_id, "⚠️ የምርት ስም በ / መጀመር አይችልም።")
            return

        bot.set_state(message.from_user.id, AddProductStates.waiting_for_category, chat_id)
        with bot.retrieve_data(message.from_user.id, chat_id) as data:
            data['name'] = name

        bot.send_message(chat_id,
            f"✅ ስም: <b>{name}</b>\n\n🗂 ምድቡን ይምረጡ፦",
            parse_mode="HTML", reply_markup=_category_markup())

    # Navigation guard: block text while waiting for category button
    @bot.message_handler(state=AddProductStates.waiting_for_category)
    def guard_category(message):
        chat_id = message.chat.id
        if message.text and (message.text.startswith('/') or 'Admin Panel' in message.text):
            bot.delete_state(message.from_user.id, chat_id)
            return
        bot.send_message(chat_id,
            "⚠️ እባክዎ ከዚህ ካሉት አዝራሮች ምድቡን ይምረጡ፦", reply_markup=_category_markup())

    # ---------------------------------------------------------------- step 2: category

    @bot.callback_query_handler(func=lambda call: call.data.startswith("admin_cat_"),
                                 state=AddProductStates.waiting_for_category)
    def process_category(call):
        chat_id  = call.message.chat.id
        category = call.data.replace("admin_cat_", "", 1)
        bot.answer_callback_query(call.id)

        bot.set_state(call.from_user.id, AddProductStates.waiting_for_brand, chat_id)
        with bot.retrieve_data(call.from_user.id, chat_id) as data:
            data['category'] = category

        bot.edit_message_text(
            f"🗂️ ምድብ: <b>{category}</b>\n\n🏷️ ብራንዱን ይምረጡ፦",
            chat_id, call.message.message_id,
            parse_mode="HTML", reply_markup=_brand_markup())

    # Navigation guard: block text while waiting for brand button
    @bot.message_handler(state=AddProductStates.waiting_for_brand)
    def guard_brand(message):
        chat_id = message.chat.id
        if message.text and (message.text.startswith('/') or 'Admin Panel' in message.text):
            bot.delete_state(message.from_user.id, chat_id)
            return
        bot.send_message(chat_id,
            "⚠️ እባክዎ ከዚህ ካሉት አዝራሮች ብራንዱን ይምረጡ፦", reply_markup=_brand_markup())

    # ---------------------------------------------------------------- step 3: brand

    @bot.callback_query_handler(func=lambda call: call.data.startswith("admin_brand_"),
                                 state=AddProductStates.waiting_for_brand)
    def process_brand(call):
        chat_id = call.message.chat.id
        brand   = call.data.replace("admin_brand_", "", 1)
        bot.answer_callback_query(call.id)

        bot.set_state(call.from_user.id, AddProductStates.waiting_for_price, chat_id)
        with bot.retrieve_data(call.from_user.id, chat_id) as data:
            data['brand'] = brand

        bot.edit_message_text(f"🏷️ ብራንድ: <b>{brand}</b>",
                              chat_id, call.message.message_id, parse_mode="HTML")
        bot.send_message(chat_id, "💵 የሚሸጥበትን ዋጋ (ETB) ያስገቡ (ምሳሌ፦ 3200)፦")

    # ---------------------------------------------------------------- step 4: base_price

    @bot.message_handler(state=AddProductStates.waiting_for_price)
    def process_price(message):
        chat_id = message.chat.id
        text    = message.text.strip() if message.text else ""
        if not text.isdigit() or int(text) <= 0:
            bot.send_message(chat_id, "⚠️ ዋጋ ከዜሮ በላይ በሆነ ሙሉ ቁጥር ያስገቡ፦")
            return

        bot.set_state(message.from_user.id, AddProductStates.waiting_for_original_price, chat_id)
        with bot.retrieve_data(message.from_user.id, chat_id) as data:
            data['base_price'] = int(text)

        bot.send_message(chat_id,
            "💰 የቀድሞ ዋጋ ያስገቡ ወይም ቅናሽ ከሌለ <code>0</code> ይጻፉ፦", parse_mode="HTML")

    # ---------------------------------------------------------------- step 5: original_price

    @bot.message_handler(state=AddProductStates.waiting_for_original_price)
    def process_original_price(message):
        chat_id = message.chat.id
        text    = message.text.strip() if message.text else ""
        if not text.isdigit():
            bot.send_message(chat_id, "⚠️ ቁጥር ብቻ ያስገቡ (ወይም 0)፦")
            return

        original = int(text)
        with bot.retrieve_data(message.from_user.id, chat_id) as data:
            if original > 0 and original <= data['base_price']:
                bot.send_message(chat_id,
                    f"⚠️ የቀድሞ ዋጋ ({original}) ከአሁኑ ዋጋ ({data['base_price']} ETB) መብለጥ አለበት፦")
                return
            data['original_price'] = original if original > 0 else None

        bot.set_state(message.from_user.id, AddProductStates.waiting_for_description, chat_id)
        bot.send_message(chat_id,
            "📝 ማብራሪያ ያስገቡ ወይም <code>skip</code> ይጻፉ፦", parse_mode="HTML")

    # ---------------------------------------------------------------- step 6: description → create product

    @bot.message_handler(state=AddProductStates.waiting_for_description)
    def process_description(message):
        chat_id = message.chat.id
        if chat_id in processing_admins:
            return
        processing_admins.add(chat_id)

        desc_text   = message.text.strip() if message.text else ""
        description = desc_text if desc_text.lower() != 'skip' else None
        load_msg    = bot.send_message(chat_id, "⏳ ዳታቤዝ ላይ እየተጫነ ነው...")

        try:
            with bot.retrieve_data(message.from_user.id, chat_id) as data:
                if not data.get('category') or not data.get('brand'):
                    bot.edit_message_text("❌ ካቴጎሪ ወይም ብራንድ አልተመረጠም። ደግሞ ይጀምሩ።",
                                          chat_id, load_msg.message_id)
                    bot.delete_state(message.from_user.id, chat_id)
                    return

                product = db.db.add_product(
                    name=data['name'],
                    category=data['category'],
                    base_price=data['base_price'],
                    description=description,
                    brand=data['brand'],
                    original_price=data.get('original_price'),
                )

                try:
                    bot.delete_message(chat_id, load_msg.message_id)
                except Exception:
                    pass

                if not product or 'id' not in product:
                    raise ValueError("product insert returned None")

                data['product_id'] = product['id']

            bot.set_state(message.from_user.id, AddProductStates.waiting_for_variant_size, chat_id)
            bot.send_message(chat_id, "✅ ምርቱ ተቀምጧል!\n\n📐 Size ያስገቡ (30–50)፦")

        except Exception as e:
            logger.error(f"process_description error: {e}")
            try:
                bot.delete_message(chat_id, load_msg.message_id)
            except Exception:
                pass
            bot.send_message(chat_id, "❌ ዳታቤዝ ስህተት ተከስቷል። ደግሞ ይሞክሩ።")
            bot.delete_state(message.from_user.id, chat_id)
        finally:
            processing_admins.discard(chat_id)

    # ---------------------------------------------------------------- step 7: variant size

    @bot.message_handler(state=AddProductStates.waiting_for_variant_size)
    def process_variant_size(message):
        chat_id = message.chat.id
        text    = message.text.strip() if message.text else ""
        if not text.isdigit() or not (30 <= int(text) <= 50):
            bot.send_message(chat_id, "⚠️ Size ከ 30 እስከ 50 ያለ ቁጥር ያስገቡ፦")
            return

        with bot.retrieve_data(message.from_user.id, chat_id) as data:
            data['variant_size'] = int(text)
        bot.set_state(message.from_user.id, AddProductStates.waiting_for_variant_color, chat_id)
        bot.send_message(chat_id, "🎨 ቀለም ያስገቡ (ምሳሌ፦ ጥቁር፣ ነጭ)፦")

    # ---------------------------------------------------------------- step 8: variant color

    @bot.message_handler(state=AddProductStates.waiting_for_variant_color)
    def process_variant_color(message):
        chat_id = message.chat.id
        raw_color = message.text.strip() if message.text else ""

        # Validate and sanitize the color
        color, is_valid, error_msg = sanitize_input(raw_color, max_length=30)
        if not is_valid:
            bot.send_message(chat_id, f"⚠️ {error_msg}")
            return

        if color.isdigit():
            bot.send_message(chat_id, "⚠️ ቀለም ቁጥር መሆን አይችልም። እባክዎ ትክክለኛ ቀለም ያስገቡ።")
            return

        with bot.retrieve_data(message.from_user.id, chat_id) as data:
            data['variant_color'] = color
        bot.set_state(message.from_user.id, AddProductStates.waiting_for_variant_stock, chat_id)
        bot.send_message(chat_id, "📦 Stock ብዛት ያስገቡ፦")

    # ---------------------------------------------------------------- step 9: variant stock

    @bot.message_handler(state=AddProductStates.waiting_for_variant_stock)
    def process_variant_stock(message):
        chat_id = message.chat.id
        text    = message.text.strip() if message.text else ""
        if not text.isdigit():
            bot.send_message(chat_id, "⚠️ ቁጥር ብቻ ያስገቡ፦")
            return

        with bot.retrieve_data(message.from_user.id, chat_id) as data:
            data['variant_stock'] = int(text)
        bot.set_state(message.from_user.id, AddProductStates.waiting_for_variant_image, chat_id)
        bot.send_message(chat_id,
            "📸 ፎቶ ይላኩ (Telegram Photo) ወይም URL ያስገቡ — ከሌለ <code>skip</code> ይጻፉ፦",
            parse_mode="HTML")

    # ---------------------------------------------------------------- step 10: variant image
    # Accepts Telegram photo OR text URL OR "skip"

    @bot.message_handler(state=AddProductStates.waiting_for_variant_image,
                         content_types=['photo', 'text'])
    def process_variant_image(message):
        chat_id          = message.chat.id
        image_url        = None
        telegram_file_id = None

        logger.info(f"Processing variant image - content_type: {message.content_type}")

        # Handle photo content type (Telegram photo)
        if message.content_type == 'photo':
            # Get the highest resolution photo (last in array)
            if message.photo and len(message.photo) > 0:
                telegram_file_id = message.photo[-1].file_id
                logger.info(f"Got Telegram photo with file_id: {telegram_file_id}")
            else:
                bot.send_message(chat_id,
                    "⚠️ ምስል ማግኘት አልተሳካም። ደግሞ ይሞክሩ።")
                return

        # Handle text content type (URL or skip)
        elif message.content_type == 'text':
            text = message.text.strip() if message.text else ""
            logger.info(f"Processing text input for image: '{text[:50]}...'")

            if text.lower() == 'skip':
                # No image - proceed with None values
                pass
            elif text.startswith('http://') or text.startswith('https://'):
                # Validate URL before using
                url, is_valid, error_msg = sanitize_url(text)
                if not is_valid:
                    bot.send_message(chat_id, f"⚠️ {error_msg}")
                    return
                image_url = url
                logger.info(f"Got valid URL: {image_url}")
            else:
                bot.send_message(chat_id,
                    "⚠️ ፎቶ ይላኩ፣ URL ያስገቡ (http://... ወይም https://...) ወይም <code>skip</code> ይጻፉ፦", parse_mode="HTML")
                return

        # Handle any other content type
        else:
            bot.send_message(chat_id,
                "⚠️ እባክዎ ፎቶ ይላኩ፣ URL ያስገቡ ወይም <code>skip</code> ይጻፉ፦", parse_mode="HTML")
            return

        try:
            with bot.retrieve_data(message.from_user.id, chat_id) as data:
                product_id = data.get('product_id')
                size = data.get('variant_size')
                color = data.get('variant_color')
                stock = data.get('variant_stock')

                # Validate we have all required data
                if not product_id or not size:
                    bot.send_message(chat_id, "❌ የሆነ ችግር ተከስቷል። ደግሞ ይጀምሩ።")
                    bot.delete_state(message.from_user.id, chat_id)
                    return

                logger.info(f"Creating variant: product={product_id}, size={size}, color={color}, stock={stock}")

                variant = db.db.add_product_variant(
                    product_id=product_id,
                    size=int(size),
                    color=str(color) if color else 'N/A',
                    stock=int(stock) if stock else 0,
                    image_url=image_url,
                    telegram_file_id=telegram_file_id,
                )

                if not variant:
                    logger.error(f"Variant creation returned None for product {product_id}")
                    bot.send_message(chat_id, "❌ Variant ማስቀመጥ አልተሳካም። ደግሞ ይሞክሩ።")
                    bot.delete_state(message.from_user.id, chat_id)
                    return

                logger.info(f"Variant created successfully: {variant.get('id', 'unknown')}")

                price_display = f"{data.get('base_price', 0)} ETB"
                if data.get('original_price'):
                    price_display = f"<s>{data['original_price']}</s> {data['base_price']} ETB"

                image_info = '🖼️ Telegram Photo ✅' if telegram_file_id else (('🔗 ' + image_url) if image_url else '📷 ምስል የለም')

                bot.send_message(chat_id,
                    f"✅ <b>Variant ተቀምጧል!</b>\n\n"
                    f"📐 Size: {size}\n"
                    f"🎨 Color: {color}\n"
                    f"📦 Stock: {stock}\n"
                    f"{image_info}",
                    parse_mode="HTML")

                markup = InlineKeyboardMarkup()
                markup.add(
                    InlineKeyboardButton("➕ ሌላ Size/Color አክል",
                                         callback_data=f"add_more_variants_{product_id}"),
                    InlineKeyboardButton("✅ ጨርሻለሁ", callback_data="finish_product"),
                )
                bot.send_message(chat_id, "ሌላ Size ወይም Color ማከል ይፈልጋሉ?", reply_markup=markup)

        except KeyError as ke:
            logger.error(f"process_variant_image KeyError: {ke}")
            bot.send_message(chat_id, "❌ የሆነ ችግር ተከስቷል። ደግሞ ይጀምሩ።")
        except Exception as e:
            logger.error(f"process_variant_image error: {e}", exc_info=True)
            bot.send_message(chat_id, "❌ ዳታቤዝ ስህተት ተከስቷል። ደግሞ ይሞክሩ።")

        bot.delete_state(message.from_user.id, chat_id)

    # ---------------------------------------------------------------- add more variants

    @bot.callback_query_handler(func=lambda call: call.data.startswith("add_more_variants_"))
    def add_more_variants(call):
        chat_id = call.message.chat.id
        if call.from_user.id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ አልተፈቀደም!", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        bot.delete_state(call.from_user.id, chat_id)

        product_id = call.data.replace("add_more_variants_", "", 1)
        bot.set_state(call.from_user.id, AddVariantStates.waiting_for_size, chat_id)
        with bot.retrieve_data(call.from_user.id, chat_id) as data:
            data['product_id'] = product_id
        bot.send_message(chat_id, "📐 አዲሱን Size ያስገቡ (30–50)፦")

    @bot.message_handler(state=AddVariantStates.waiting_for_size)
    def process_new_variant_size(message):
        chat_id = message.chat.id
        text    = message.text.strip() if message.text else ""
        if not text.isdigit() or not (30 <= int(text) <= 50):
            bot.send_message(chat_id, "⚠️ Size ከ 30 እስከ 50 ያለ ቁጥር ያስገቡ፦")
            return
        with bot.retrieve_data(message.from_user.id, chat_id) as data:
            data['variant_size'] = int(text)
        bot.set_state(message.from_user.id, AddVariantStates.waiting_for_color, chat_id)
        bot.send_message(chat_id, "🎨 ቀለም ያስገቡ፦")

    @bot.message_handler(state=AddVariantStates.waiting_for_color)
    def process_new_variant_color(message):
        chat_id = message.chat.id
        raw_color = message.text.strip() if message.text else ""

        color, is_valid, error_msg = sanitize_input(raw_color, max_length=30)
        if not is_valid:
            bot.send_message(chat_id, f"⚠️ {error_msg}")
            return

        if color.isdigit():
            bot.send_message(chat_id, "⚠️ ቀለም ቁጥር መሆን አይችልም። እባክዎ ትክክለኛ ቀለም ያስገቡ፦")
            return

        with bot.retrieve_data(message.from_user.id, chat_id) as data:
            data['variant_color'] = color
        bot.set_state(message.from_user.id, AddVariantStates.waiting_for_stock, chat_id)
        bot.send_message(chat_id, "📦 Stock ብዛት ያስገቡ፦")

    @bot.message_handler(state=AddVariantStates.waiting_for_stock)
    def process_new_variant_stock(message):
        chat_id = message.chat.id
        text    = message.text.strip() if message.text else ""
        if not text.isdigit():
            bot.send_message(chat_id, "⚠️ ቁጥር ብቻ ያስገቡ፦")
            return
        with bot.retrieve_data(message.from_user.id, chat_id) as data:
            data['variant_stock'] = int(text)
        bot.set_state(message.from_user.id, AddVariantStates.waiting_for_image, chat_id)
        bot.send_message(chat_id,
            "📸 ፎቶ ይላኩ፣ URL ያስገቡ ወይም <code>skip</code> ይጻፉ፦", parse_mode="HTML")

    @bot.message_handler(state=AddVariantStates.waiting_for_image,
                         content_types=['photo', 'text'])
    def process_new_variant_image(message):
        chat_id          = message.chat.id
        image_url        = None
        telegram_file_id = None

        logger.info(f"Processing new variant image - content_type: {message.content_type}")

        if message.content_type == 'photo':
            if message.photo and len(message.photo) > 0:
                telegram_file_id = message.photo[-1].file_id
                logger.info(f"Got Telegram photo with file_id: {telegram_file_id}")
            else:
                bot.send_message(chat_id, "⚠️ ምስል ማግኘት አልተሳካም።")
                return

        elif message.content_type == 'text':
            text = message.text.strip() if message.text else ""
            if text.lower() == 'skip':
                pass
            elif text.startswith('http://') or text.startswith('https://'):
                # Validate URL
                url, is_valid, error_msg = sanitize_url(text)
                if not is_valid:
                    bot.send_message(chat_id, f"⚠️ {error_msg}")
                    return
                image_url = url
            else:
                bot.send_message(chat_id,
                    "⚠️ ፎቶ ይላኩ፣ URL ያስገቡ (http://... ወይም https://...) ወይም <code>skip</code> ይጻፉ፦", parse_mode="HTML")
                return
        else:
            bot.send_message(chat_id,
                "⚠️ እባክዎ ፎቶ ይላኩ፣ URL ያስገቡ ወይም <code>skip</code> ይጻፉ፦", parse_mode="HTML")
            return

        try:
            with bot.retrieve_data(message.from_user.id, chat_id) as data:
                product_id = data.get('product_id')
                size = data.get('variant_size')
                color = data.get('variant_color')
                stock = data.get('variant_stock')

                if not product_id or not size:
                    bot.send_message(chat_id, "❌ የሆነ ችግር ተከስቷል። ደግሞ ይጀምሩ።")
                    bot.delete_state(message.from_user.id, chat_id)
                    return

                logger.info(f"Creating additional variant: product={product_id}, size={size}, color={color}")

                variant = db.db.add_product_variant(
                    product_id=product_id,
                    size=int(size),
                    color=str(color) if color else 'N/A',
                    stock=int(stock) if stock else 0,
                    image_url=image_url,
                    telegram_file_id=telegram_file_id,
                )

                if variant:
                    image_info = '🖼️ Telegram Photo ✅' if telegram_file_id else (('🔗 ' + image_url) if image_url else '📷 ምስል የለም')
                    bot.send_message(chat_id,
                        f"✅ Size {size} / {color} ተቀምጧል!\n{image_info}")
                    markup = InlineKeyboardMarkup()
                    markup.add(
                        InlineKeyboardButton("➕ ሌላ ማከል",
                                             callback_data=f"add_more_variants_{product_id}"),
                        InlineKeyboardButton("✅ ጨርሻለሁ", callback_data="finish_product"),
                    )
                    bot.send_message(chat_id, "ሌላ ማከል ይፈልጋሉ?", reply_markup=markup)
                else:
                    bot.send_message(chat_id, "❌ ማስቀመጥ አልተሳካም። ደግሞ ይሞክሩ።")

        except Exception as e:
            logger.error(f"process_new_variant_image error: {e}", exc_info=True)
            bot.send_message(chat_id, "❌ ዳታቤዝ ስህተት ተከስቷል። ደግሞ ይሞክሩ።")

        bot.delete_state(message.from_user.id, chat_id)

    # ---------------------------------------------------------------- finish

    @bot.callback_query_handler(func=lambda call: call.data == "finish_product")
    def finish_product(call):
        bot.answer_callback_query(call.id, "✅ ምዝገባ ተጠናቋል!")
        bot.delete_state(call.from_user.id, call.message.chat.id)
        bot.send_message(call.message.chat.id,
            "👌 ምርቱ ሙሉ በሙሉ ተቀምጧል። Admin Panel ን መጠቀም ይችላሉ።")
