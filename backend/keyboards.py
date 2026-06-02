# backend/keyboards.py - Telegram keyboard layouts
# Ethio Shoe Store Telegram Bot

from telebot import types

def get_main_menu():
    """Get main menu reply keyboard for customers."""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("👟 ምርቶችን እይ"),
        types.KeyboardButton("🛒 ጋሪዬ")
    )
    keyboard.add(
        types.KeyboardButton("🛍️ የእኔ ትዕዛዞች"),
        types.KeyboardButton("📞 እኛን ለማግኘት")
    )
    return keyboard

def get_admin_main_menu():
    """Get admin main menu reply keyboard."""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("🔐 Admin Panel"),
        types.KeyboardButton("👟 ምርቶችን እይ")
    )
    keyboard.add(
        types.KeyboardButton("🛍️ የእኔ ትዕዛዞች"),
        types.KeyboardButton("🔄 ወደ ዋና ማውጫ")
    )
    return keyboard

def get_admin_panel_keyboard():
    """Get admin panel inline keyboard."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("📦 አዳዲስ ትዕዛዞችን ይመልከቱ", callback_data="admin_view_orders"),
        types.InlineKeyboardButton("➕ ምርት አክል", callback_data="admin_add_product"),
        types.InlineKeyboardButton("📊 Reports", callback_data="admin_reports")
    )
    return keyboard

def get_category_menu():
    """Get product categories menu."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👞 የወንዶች", callback_data="cat_የወንዶች"),
        types.InlineKeyboardButton("👠 የሴቶች", callback_data="cat_የሴቶች"),
        types.InlineKeyboardButton("👟 የህፃናት", callback_data="cat_የህፃናት"),
        types.InlineKeyboardButton("👥 የሁለቱም", callback_data="cat_የሁለቱም")
    )
    return markup

def get_product_detail_keyboard(product_id):
    """Get product detail inline keyboard."""
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        types.InlineKeyboardButton("🛒 ወደ ጋሪ አክል", callback_data=f"product_{product_id}")
    )
    return keyboard

def get_size_selection_keyboard(product_id, sizes):
    """Get size selection inline keyboard."""
    keyboard = types.InlineKeyboardMarkup(row_width=4)
    buttons = [
        types.InlineKeyboardButton(str(size), callback_data=f"size_{product_id}_{size}")
        for size in sizes
    ]
    keyboard.add(*buttons)
    return keyboard

def get_color_selection_keyboard(product_id, size, colors):
    """Get color selection inline keyboard."""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(color, callback_data=f"color_{product_id}_{size}_{color}")
        for color in colors
    ]
    keyboard.add(*buttons)
    return keyboard

def get_cart_checkout_keyboard():
    """Get cart checkout inline keyboard - Fixed mixed button types"""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("✅ ማረጋገጫ (Checkout)", callback_data="checkout"),
        types.InlineKeyboardButton("🗑️ ጋሪውን አጽዳ", callback_data="clear_cart_action")
    )
    return keyboard

def get_order_status_keyboard(order_id):
    """Get order status update inline keyboard for admins."""
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("✅ ተረጋግጧል", callback_data=f"status_{order_id}_confirmed"),
        types.InlineKeyboardButton("🚚 ተልኳል", callback_data=f"status_{order_id}_shipped")
    )
    keyboard.add(
        types.InlineKeyboardButton("📦 ተጠናቋል", callback_data=f"status_{order_id}_delivered"),
        types.InlineKeyboardButton("❌ ተሰርዟል", callback_data=f"status_{order_id}_cancelled")
    )
    return keyboard

# ============================================================
# NEW KEYBOARDS FOR THE REWRITTEN CHECKOUT & PAYMENT FLOWS
# ============================================================

def get_allowed_cities_keyboard():
    """Get checkout city selection reply keyboard matching backend validation rules."""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
    # Allowed cities checklist in the database manager
    cities = [
        "Addis Ababa", "Adama", "Hawassa", "Bahir Dar", "Dire Dawa",
        "Mekelle", "Gondar", "Jimma", "Dessie", "Shashamane"
    ]
    buttons = [types.KeyboardButton(city) for city in cities]
    keyboard.add(*buttons)
    return keyboard

def get_payment_methods_keyboard():
    """Get system payment provider selection reply keyboard."""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
    keyboard.add(
        types.KeyboardButton("telebirr"),
        types.KeyboardButton("cbe")
    )
    return keyboard