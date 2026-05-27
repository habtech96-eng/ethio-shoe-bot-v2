from telebot import types

# ⌨️ የዋና ማውጫ በተኖች (Main Menu)
def get_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("👟 ምርቶችን እይ")
    btn2 = types.KeyboardButton("📞 እኛን ለማግኘት")
    btn3 = types.KeyboardButton("🛍️ የእኔ ትዕዛዞች")
    markup.add(btn1)
    markup.add(btn2, btn3)
    return markup

# 🗂️ የምድብ ማውጫ በተኖች (Category Menu)
def get_category_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("👞 የወንዶች ጫማዎች")
    btn2 = types.KeyboardButton("👠 የሴቶች ጫማዎች")
    btn3 = types.KeyboardButton("👟 የህፃናት ጫማዎች")
    btn4 = types.KeyboardButton("👥 የሁለቱም/Unisex")
    btn5 = types.KeyboardButton("🔄 ወደ ዋና ማውጫ")
    markup.add(btn1, btn2)
    markup.add(btn3, btn4)
    markup.add(btn5)
    return markup

# 🛍️ የእያንዳንዱ ምርት መግዣ በተን (Inline Button)
def get_buy_inline_keyboard(product_id):
    inline_markup = types.InlineKeyboardMarkup()
    buy_btn = types.InlineKeyboardButton("🛍️ አሁኑኑ እዘዝ", callback_data=f"buy_{product_id}")
    inline_markup.add(buy_btn)
    return inline_markup

    # keyboards.py (ከቀድሞው ኮድ በታች የሚቀጥል)

# 👨‍💼 የአድሚን ዋና ማውጫ (የተራ ደንበኛ ማውጫ + የአድሚን በተን)
def get_admin_main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("👟 ምርቶችን እይ")
    btn2 = types.KeyboardButton("📞 እኛን ለማግኘት")
    btn3 = types.KeyboardButton("🛍️ የእኔ ትዕዛዞች")
    btn_admin = types.KeyboardButton("🔐 Admin Panel") # 👈 ለአድሚን ብቻ የሚታይ
    markup.add(btn1)
    markup.add(btn2, btn3)
    markup.add(btn_admin)
    return markup

# 🛠️ የአድሚን መቆጣጠሪያ ሰሌዳ (Inline Buttons)
def get_admin_panel_keyboard():
    inline_markup = types.InlineKeyboardMarkup(row_width=1)
    btn_view_orders = types.InlineKeyboardButton("📋 ሁሉንም ትዕዛዞች እይ", callback_data="admin_view_orders")
    btn_add_product = types.InlineKeyboardButton("➕ አዲስ ምርት ጨምር", callback_data="admin_add_product")
    inline_markup.add(btn_view_orders, btn_add_product)
    return inline_markup 

# keyboards.py (ከፋይሉ መጨረሻ ላይ ቀጥሎ የሚጻፍ)

# 📞 የቴሌግራም ስልክ ቁጥርን በራሱ አውቶማቲክ የሚያመጣ በተን
def get_phone_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    # request_contact=True ሲሆን ስልኩን በራሱ ይልካል
    btn_phone = types.KeyboardButton("📱 ስልኬን በራስ-ሰር ላክ (Share Contact)", request_contact=True)
    markup.add(btn_phone)
    return markup

# 📍 ለአድራሻ የሚሆኑ ቀላሉ አማራጮች በተን
def get_location_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    btn1 = types.KeyboardButton("📍 አዲስ አበባ (ከተማ ውስጥ)")
    btn2 = types.KeyboardButton("🚚 በፖስታ/በመኪና (ከአዲስ አበባ ውጭ)")
    markup.add(btn1, btn2)
    return markup

# 🎯 Product detail keyboard
def get_product_detail_keyboard(product_id):
    inline_markup = types.InlineKeyboardMarkup(row_width=1)
    btn_detail = types.InlineKeyboardButton("🛒 ለመግዛት ይምረጡ", callback_data=f"product_{product_id}")
    inline_markup.add(btn_detail)
    return inline_markup

# 📐 Size selection keyboard
def get_size_selection_keyboard(product_id, sizes):
    inline_markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    for size in sizes:
        buttons.append(types.InlineKeyboardButton(f"📐 {size}", callback_data=f"size_{product_id}_{size}"))
    inline_markup.add(*buttons)
    return inline_markup

# 🎨 Color selection keyboard
def get_color_selection_keyboard(product_id, size, colors):
    inline_markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []
    for color in colors:
        buttons.append(types.InlineKeyboardButton(f"🎨 {color}", callback_data=f"color_{product_id}_{size}_{color}"))
    inline_markup.add(*buttons)
    return inline_markup

# 🛒 Cart checkout keyboard
def get_cart_checkout_keyboard():
    inline_markup = types.InlineKeyboardMarkup(row_width=2)
    btn_checkout = types.InlineKeyboardButton("✅ ወደ ክፍያ ሂድ", callback_data="checkout")
    btn_clear = types.InlineKeyboardButton("🗑️ ጋሪ አጽዳ", callback_data="clear_cart")
    inline_markup.add(btn_checkout, btn_clear)
    return inline_markup