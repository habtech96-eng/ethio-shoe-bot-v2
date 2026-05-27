# handlers.py
from config import ADMIN_IDS
import keyboards
import database # 👈 ዳታቤዙን አስገባን

def register_handlers(bot):
    
    @bot.message_handler(commands=['start'])
    def send_welcome(message):
        chat_id = message.chat.id
        if chat_id in ADMIN_IDS:
            bot.send_message(chat_id, f"👨‍💼 ሰላም አድሚን {message.from_user.first_name}!", reply_markup=keyboards.get_admin_main_menu())
        else:
            bot.send_message(chat_id, f"👋 እንኳን ወደ Ethio Shoe Store በደህና መጡ፣ {message.from_user.first_name}!", reply_markup=keyboards.get_main_menu())

    @bot.message_handler(func=lambda message: True)
    def handle_messages(message):
        chat_id = message.chat.id
        text = message.text.strip()

        if text == "🔐 Admin Panel":
            if chat_id in ADMIN_IDS:
                bot.send_message(chat_id, "🛠️ የአድሚን ማዘዣ ሰሌዳ፦", reply_markup=keyboards.get_admin_panel_keyboard())
            else:
                bot.send_message(chat_id, "⚠️ ይቅርታ፣ ይህ አልተፈቀደም።")

        elif text == "🔄 ወደ ዋና ማውጫ":
            reply_keyboard = keyboards.get_admin_main_menu() if chat_id in ADMIN_IDS else keyboards.get_main_menu()
            bot.send_message(chat_id, "🏠 ወደ ዋና ማውጫ ተመልሰዋል።", reply_markup=reply_keyboard)
            
        elif text == "👟 ምርቶችን እይ":
            bot.send_message(chat_id, "🗂️ እባክህ የምትፈልገውን የምድብ አይነት ምረጥ፦", reply_markup=keyboards.get_category_menu())
            
        elif text in ["👞 የወንዶች ጫማዎች", "👠 የሴቶች ጫማዎች"]:
            category = "የወንዶች" if "የወንዶች" in text else "የሴቶች"
            # 💾 ከዳታቤዝ ማውጫ
            filtered_products = database.get_products_by_category(category)
            
            if not filtered_products:
                bot.send_message(chat_id, f"⚠️ በአሁኑ ሰዓት በ '{category}' ምድብ ስር ምንም ምርት የለም።")
                return

            # handlers.py (የምርት ማሳያ ሉፕ ማሻሻያ)

            for p in filtered_products:
                caption = f"👟 **{p['name']}**\n\n💵 **ዋጋ፦** {p['price']} ብር\n📐 **ያለው ሳይዝ፦** {p['size']}\n📦 **በስቶክ ያለው ብዛት፦** {p['stock']} ጥንድ"
                
                # 🖼️ ፎቶ ካለው በ send_photo፣ ከሌለው በ send_message ያሳያል
                if p.get('photo'):
                    bot.send_photo(
                        chat_id, 
                        p['photo'], 
                        caption=caption, 
                        parse_mode="Markdown", 
                        reply_markup=keyboards.get_buy_inline_keyboard(p['id'])
                    )
                else:
                    bot.send_message(
                        chat_id, 
                        caption, 
                        parse_mode="Markdown", 
                        reply_markup=keyboards.get_buy_inline_keyboard(p['id'])
                    )

        elif text == "📞 እኛን ለማግኘት":
            bot.send_message(chat_id, "📞 እኛን ለማግኘት በስልክ ቁጥር +2519XXXXXXXX መደወል ይችላሉ።")
            
        # handlers.py (የ "🛍️ የእኔ ትዕዛዞች" ክፍል ማሻሻያ)

        elif text == "🛍️ የእኔ ትዕዛዞች":
            # 💾 ከዳታቤዝ በ chat_id መፈለግ
            user_orders = database.get_user_orders(chat_id)
            
            if not user_orders:
                bot.send_message(chat_id, "📦 በአሁኑ ሰዓት ምንም አይነት ያላጠናቀቁት ትዕዛዝ የለም።")
                return
                
            bot.send_message(chat_id, "🛍️ **የእርስዎ የትዕዛዞች ዝርዝር፦**")
            for o in user_orders:
                order_text = f"🆔 **የትዕዛዝ ቁጥር:** #{o['order_id']}\n👟 **ምርት:** {o['product_name']}\n🚦 **ሁኔታ:** {o['status']}"
                bot.send_message(chat_id, order_text, parse_mode="Markdown")

    # 🛍️ የኢንላይን በተኖች ንክኪ (Callback Query)
    @bot.callback_query_handler(func=lambda call: True)
    def handle_callback(call):
        chat_id = call.message.chat.id
        
        # የአድሚን ትዕዛዞችን ማሳያ በተን
        if call.data == "admin_view_orders":
            if chat_id in ADMIN_IDS:
                bot.answer_callback_query(call.id)
                orders = database.get_all_orders()
                if not orders:
                    bot.send_message(chat_id, "📭 በአሁኑ ሰዓት ምንም የገባ ትዕዛዝ የለም።")
                    return
                
                bot.send_message(chat_id, "📦 **የገቡ አዳዲስ ትዕዛዞች ዝርዝር፦**")
                for o in orders:
                    order_text = f"🆔 **ትዕዛዝ ID:** #{o['order_id']}\n👤 **ደንበኛ:** {o['user_name']}\n👟 **ምርት:** {o['product_name']}\n📞 **ስልክ:** {o['phone']}\n🚦 **ሁኔታ:** {o['status']}"
                    bot.send_message(chat_id, order_text, parse_mode="Markdown")
            else:
                bot.answer_callback_query(call.id, text="እርምጃው አልተፈቀደም!", show_alert=True)