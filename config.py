# config.py

BOT_TOKEN = "[SET_VIA_ENVIRONMENT_VARIABLE_NEVER_COMMIT_TOKENS]"

# 🔒 የአድሚኖች Chat ID ዝርዝር
ADMIN_IDS = [7098279917] 

# 🗄️ ምርቶች (ይህንን በቀጣይ ወደ ቋሚ ዳታቤዝ እንቀይረዋለን)
PRODUCTS = [
    {"id": "1", "name": "የወንዶች ስፖርት ጫማ", "category": "የወንዶች", "price": "2500", "stock": "10", "size": "42"},
    {"id": "2", "name": "የሴቶች ተረከዝ ጫማ", "category": "የሴቶች", "price": "3200", "stock": "5", "size": "38"}
]

# 🛍️ ለሙከራ የሚሆን የትዕዛዞች ዝርዝር
ORDERS = [
    {"order_id": "1001", "user": "Gosa", "product": "የወንዶች ስፖርት ጫማ", "phone": "0911223344", "status": "⏱️ ይጠበቃል"}
]