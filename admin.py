# admin.py
import telebot
from telebot.handler_backends import State, StatesGroup
from config import ADMIN_IDS
import keyboards
import database

class AddProductStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_category = State()
    waiting_for_price = State()
    waiting_for_size = State()
    waiting_for_photo = State() # 👈 አዲስ የስቴት ደረጃ

def register_admin_handlers(bot):
    
    @bot.callback_query_handler(func=lambda call: call.data == "admin_add_product")
    def start_add_product(call):
        chat_id = call.message.chat.id
        if chat_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ ይህ እርምጃ ለእርስዎ አልተፈቀደም!", show_alert=True)
            return
        bot.answer_callback_query(call.id)
        bot.send_message(chat_id, "📝 የእቃውን ስም (Product Name) ያስገቡ፦")
        bot.set_state(chat_id, AddProductStates.waiting_for_name)

    @bot.message_handler(state=AddProductStates.waiting_for_name)
    def process_name(message):
        chat_id = message.chat.id
        with bot.retrieve_data(chat_id) as data:
            data['name'] = message.text.strip()
        bot.send_message(chat_id, "🗂️ የምርት ምድብ ይምረጡ፦", reply_markup=keyboards.get_category_menu())
        bot.set_state(chat_id, AddProductStates.waiting_for_category)

    @bot.message_handler(state=AddProductStates.waiting_for_category)
    def process_category(message):
        chat_id = message.chat.id
        text = message.text.strip()
        category = "የወንዶች" if "የወንዶች" in text else "የሴቶች" if "የሴቶች" in text else text
        with bot.retrieve_data(chat_id) as data:
            data['category'] = category
        markup = telebot.types.ReplyKeyboardRemove()
        bot.send_message(chat_id, "💵 የምርቱን ዋጋ በብር ብቻ ያስገቡ (ምሳሌ፦ 2500)፦", reply_markup=markup)
        bot.set_state(chat_id, AddProductStates.waiting_for_price)

    @bot.message_handler(state=AddProductStates.waiting_for_price)
    def process_price(message):
        chat_id = message.chat.id
        price = message.text.strip()
        if not price.isdigit():
            bot.send_message(chat_id, "⚠️ እባክህ ዋጋውን በቁጥር ብቻ አስገባ፦")
            return
        with bot.retrieve_data(chat_id) as data:
            data['price'] = price
        bot.send_message(chat_id, "📐 ያሉት ሳይዞች ዝርዝር ያስገቡ (ምሳሌ፦ 40-44)፦")
        bot.set_state(chat_id, AddProductStates.waiting_for_size)

    # 🖼️ አዲስ፦ የሳይዝ መቀበያ አሁን ፎቶ እንዲጠይቅ ያደርጋል
    @bot.message_handler(state=AddProductStates.waiting_for_size)
    def process_size(message):
        chat_id = message.chat.id
        with bot.retrieve_data(chat_id) as data:
            data['size'] = message.text.strip()
            
        bot.send_message(chat_id, "📸 አሁን ደግሞ የጫማውን ፎቶ ይላኩ (Photo ብቻ)፦")
        bot.set_state(chat_id, AddProductStates.waiting_for_photo)

    # 🖼️ አዲስ፦ የፎቶ መቀበያ እና ማጠቃለያ
    @bot.message_handler(state=AddProductStates.waiting_for_photo, content_types=['photo'])
    def process_photo(message):
        chat_id = message.chat.id
        
        # የላቀ ጥራት ያለውን ፎቶ file_id መውሰድ [-1] ማለት ትልቁ ማለት ነው
        photo_id = message.photo[-1].file_id
        
        with bot.retrieve_data(chat_id) as data:
            # ወደ ዳታቤዝ በፎቶ አይዲው ማስቀመጥ
            database.add_product(data['name'], data['category'], data['price'], data['size'], photo_id)
            saved_data = data.copy()
            
        bot.delete_state(chat_id)
        
        success_text = f"✅ **ምርቱ ከነፎቶው በዳታቤዝ ውስጥ ተቀምጧል!**\n\n📦 **ስም፦** {saved_data['name']}\n🗂️ **%E1%8A%9D%E1%8B%B5%E1%89%A5፦** {saved_data['category']}\n💵 **ዋጋ፦** {saved_data['price']} ብር\n📐 **ሳይዝ፦** {saved_data['size']}"
        bot.send_photo(chat_id, photo_id, caption=success_text, parse_mode="Markdown", reply_markup=keyboards.get_admin_main_menu())