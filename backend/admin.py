# backend/admin.py
"""
Admin handlers for Ethio Shoe Store
Full operations for managing footwear products and variants with strict state navigation validation.
Fully integrated with DatabaseManager abstractions.
"""
import sys
import os
import logging
import telebot
from telebot.handler_backends import State, StatesGroup
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# ከባክኤንድ ፓኬጅ ውስጥ ዳታቤዙን ማገናኘት
from . import database as db

# አድሚን መለያዎችን ከconfig ፋይል ላይ ማንበብ
try:
    from config import ADMIN_IDS
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import ADMIN_IDS

logger = logging.getLogger(__name__)

# አድሚኖች በተከታታይ መልዕክት ሲልኩ መደራረብን መከላከያ (Race Condition Lock)
processing_admins = set()

# ምርት እና የጫማ መጠን/ቀለም ለመጨመር የሚያገለግሉ የስቴት ደረጃዎች
class AddProductStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_category = State()
    waiting_for_brand = State()
    waiting_for_price = State()
    waiting_for_original_price = State()
    waiting_for_description = State()
    waiting_for_variant_size = State()
    waiting_for_variant_color = State()
    waiting_for_variant_stock = State()
    waiting_for_variant_image = State()

class AddVariantStates(StatesGroup):
    waiting_for_size = State()
    waiting_for_color = State()
    waiting_for_stock = State()
    waiting_for_image = State()

def register_admin_handlers(bot):
    
    # 👟 1. አዲስ ጫማ መመዝገቢያ መጀመሪያ
    @bot.callback_query_handler(func=lambda call: call.data == "admin_add_product")
    def start_add_product(call):
        chat_id = call.message.chat.id
        telegram_id = call.from_user.id
        
        # ደህንነት ማረጋገጫ - በቴሌግራም መታወቂያ
        if telegram_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ ይህ የአድሚን ተግባር ለእርስዎ አልተፈቀደም!", show_alert=True)
            return
        
        bot.answer_callback_query(call.id)
        bot.delete_state(chat_id)
        if chat_id in processing_admins:
            processing_admins.remove(chat_id)
        
        bot.send_message(chat_id, "👟 እባክዎ የጫማውን ሙሉ ስም (Model Name) ያስገቡ፦\n(ምሳሌ፦ Nike Air Jordan 4)")
        bot.set_state(chat_id, AddProductStates.waiting_for_name)

   # 🗂️ 2. የጫማ ስም መቀበያ እና የክፍል (Category) ምርጫ ማሳያ
    @bot.message_handler(state=AddProductStates.waiting_for_name)
    def process_name(message):
        chat_id = message.chat.id
        product_name = message.text.strip()
        
        if len(product_name) < 2 or product_name.startswith('/') or product_name.isdigit():
            bot.send_message(chat_id, "⚠️ እባክዎ ትክክለኛ የጫማ ስም ያስገቡ፦")
            return

        with bot.retrieve_data(chat_id) as data:
            data['name'] = product_name
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("👞 የወንዶች", callback_data="cat_የወንዶች"),
            InlineKeyboardButton("👠 የሴቶች", callback_data="cat_የሴቶች"),
            InlineKeyboardButton("👶 የህፃናት", callback_data="cat_የህፃናት"),
            InlineKeyboardButton("👥 የሁለቱም", callback_data="cat_የሁለቱም/Unisex")
        )
        # እዚህ ጋር ስቴቱን ወደ waiting_for_category እንቀይራለን
        bot.set_state(chat_id, AddProductStates.waiting_for_category)
        bot.send_message(chat_id, "🗂️ እባክዎ ከታች ካሉት አዝራሮች የጫማውን የክፍል (Category) አይነት ይምረጡ፦", reply_markup=markup)

    # 🛡️ STERN NAVIGATION GUARD ለ Category (ጽሑፍ እንዳይቀበል መከላከያ)
    @bot.message_handler(state=AddProductStates.waiting_for_category)
    def guard_category(message):
        chat_id = message.chat.id
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("👞 የወንዶች", callback_data="cat_የወንዶች"),
            InlineKeyboardButton("👠 የሴቶች", callback_data="cat_የሴቶች"),
            InlineKeyboardButton("👶 የህፃናት", callback_data="cat_የህፃናት"),
            InlineKeyboardButton("👥 የሁለቱም", callback_data="cat_የሁለቱም/Unisex")
        )
        bot.send_message(chat_id, "⚠️ ስህተት፦ እባክዎ በጽሑፍ አይጻፉ! ከላይ ካሉት አዝራሮች አንዱን መምረጥ አለብዎት፦", reply_markup=markup)

    # 🏷️ 3. የጫማ ክፍል መቀበያ እና የብራንድ ምርጫ ማሳያ
    @bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"), state=AddProductStates.waiting_for_category)
    def process_category(call):
        chat_id = call.message.chat.id
        category = call.data.replace("cat_", "")
        bot.answer_callback_query(call.id)
        
        with bot.retrieve_data(chat_id) as data:
            data['category'] = category
        
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("Nike", callback_data="brand_Nike"),
            InlineKeyboardButton("Adidas", callback_data="brand_Adidas"),
            InlineKeyboardButton("Puma", callback_data="brand_Puma"),
            InlineKeyboardButton("Reebok", callback_data="brand_Reebok"),
            InlineKeyboardButton("Jordan", callback_data="brand_Jordan"),
            InlineKeyboardButton("ሀገር በቀል (Local)", callback_data="brand_Local"),
            InlineKeyboardButton("ሌላ (Other)", callback_data="brand_Other")
        )
        # እዚህ ጋር ስቴቱን ወደ waiting_for_brand እንቀይራለን
        bot.set_state(chat_id, AddProductStates.waiting_for_brand)
        bot.edit_message_text(f"🗂️ የተመረጠው ክፍል፦ {category}\n\n🏷️ በመቀጠል እባክዎ የጫማውን ብራንድ (Brand) ይምረጡ፦", chat_id, call.message.message_id, reply_markup=markup)

    # 🛡️ STERN NAVIGATION GUARD ለ Brand (ጽሑፍ እንዳይቀበል መከላከያ)
    @bot.message_handler(state=AddProductStates.waiting_for_brand)
    def guard_brand(message):
        chat_id = message.chat.id
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("Nike", callback_data="brand_Nike"),
            InlineKeyboardButton("Adidas", callback_data="brand_Adidas"),
            InlineKeyboardButton("Puma", callback_data="brand_Puma"),
            InlineKeyboardButton("Reebok", callback_data="brand_Reebok"),
            InlineKeyboardButton("Jordan", callback_data="brand_Jordan")
        )
        bot.send_message(chat_id, "⚠️ ስህተት፦ እባክዎ በጽሑፍ አይጻፉ! ከላይ ካሉት የብራንድ አዝራሮች አንዱን ይጫኑ፦", reply_markup=markup)
    # 💵 4. የብራንድ መቀበያ እና የመሸጫ ዋጋ ጥያቄ
    @bot.callback_query_handler(func=lambda call: call.data.startswith("brand_"), state=AddProductStates.waiting_for_brand)
    def process_brand(call):
        chat_id = call.message.chat.id
        brand_name = call.data.replace("brand_", "")
        bot.answer_callback_query(call.id)
        
        with bot.retrieve_data(chat_id) as data:
            data['brand'] = brand_name
        
        bot.edit_message_text(f"🏷️ የተመረጠው ብራንድ፦ {brand_name}", chat_id, call.message.message_id)
        bot.send_message(chat_id, "💵 ጫማው የሚሸጥበትን መደበኛ ዋጋ በቁጥር ብቻ ያስገቡ (ምሳሌ፦ 3200)፦")
        bot.set_state(chat_id, AddProductStates.waiting_for_price)

    # 💰 5. የመሸጫ ዋጋ ማረጋገጫ እና የቅናሽ/የድሮ ዋጋ ጥያቄ
    @bot.message_handler(state=AddProductStates.waiting_for_price)
    def process_price(message):
        chat_id = message.chat.id
        price_text = message.text.strip()
        
        if not price_text.isdigit() or int(price_text) <= 0:
            bot.send_message(chat_id, "⚠️ ስህተት፦ እባክዎ የመሸጫ ዋጋውን ከዜሮ በላይ በሆነ ቁጥር ብቻ ያስገቡ፦")
            return
        
        with bot.retrieve_data(chat_id) as data:
            data['base_price'] = float(price_text)
        
        bot.send_message(chat_id, "💰 ለደንበኞች የዋጋ ቅናሽ ለማሳየት የድሮውን ዋጋ (Original Price) ያስገቡ፣ ቅናሽ ከሌለው 0 ይጻፉ፦")
        bot.set_state(chat_id, AddProductStates.waiting_for_original_price)

    # 📝 6. የድሮ ዋጋ ማረጋገጫ እና ስለ ጫማው ማብራሪያ ጥያቄ
    @bot.message_handler(state=AddProductStates.waiting_for_original_price)
    def process_original_price(message):
        chat_id = message.chat.id
        original_text = message.text.strip()
        
        if not original_text.isdigit():
            bot.send_message(chat_id, "⚠️ ስህተት፦ እባክዎ የድሮውን ዋጋ በቁጥር ብቻ ያስገቡ (ወይም 0 ይጻፉ)፦")
            return
        
        original_price = float(original_text)
        
        with bot.retrieve_data(chat_id) as data:
            if original_price > 0 and original_price <= data['base_price']:
                bot.send_message(chat_id, f"⚠️ ስህተት፦ የድሮው ዋጋ አሁን ከሚሸጥበት ዋጋ ({data['base_price']} ETB) መብለጥ አለበት። እባክዎ ደግመው ያስገቡ፦")
                return
            data['original_price'] = original_price if original_price > 0 else None
        
        bot.send_message(chat_id, "📝 ስለ ጫማው ጥራት ወይም የተሰራበትን ማቴሪያል የሚገልጽ አጭር ማብራሪያ ያስገቡ፣ ወይም ለመዝለል 'skip' ይጻፉ፦")
        bot.set_state(chat_id, AddProductStates.waiting_for_description)

    # 📐 7. ማብራሪያ መቀበያ፣ ዋና ምርት መፍጠሪያ እና የመጀመሪያ መጠን (Size) ጥያቄ
    @bot.message_handler(state=AddProductStates.waiting_for_description)
    def process_description(message):
        chat_id = message.chat.id
        
        if chat_id in processing_admins:
            return
            
        description_text = message.text.strip()
        
        if "የተሰራበትን ማቴሪያል" in description_text and description_text.lower() != 'skip':
            bot.send_message(chat_id, "⚠️ እባክዎ በትክክል የጫማውን መግለጫ ይጻፉ ወይም ለመዝለል 'skip' ብቻ ይበሉ፦")
            return

        description = description_text if description_text.lower() != 'skip' else None
        
        processing_admins.add(chat_id)
        load_msg = bot.send_message(chat_id, "⏳ መረጃው ዳታቤዝ ላይ እየተጫነ ነው፣ እባክዎ ይጠብቁ...")

        try:
            with bot.retrieve_data(chat_id) as data:
                if not data.get('name') or not data.get('category') or not data.get('base_price'):
                    raise ValueError("Core fields missing in FSM state.")
                
                # 🔄 በ database.py ላይ ያለውን የ DatabaseManager ዝግጁ ፈንክሽን መጠቀም
                product = db.db.add_product(
                    name=data['name'],
                    category=data['category'],
                    base_price=data['base_price'],
                    description=description,
                    brand=data['brand'],
                    original_price=data.get('original_price')
                )
                
                bot.delete_message(chat_id, load_msg.message_id)
                
                if not product:
                    bot.send_message(chat_id, "❌ ስህተት፦ የጫማውን መረጃ ዳታቤዝ ላይ መጫን አልተሳካም። እባክዎ ካቴጎሪ ወይም ብራንድ ትክክል መሆኑን አረጋግጠው ከአዲስ ይጀምሩ።")
                    bot.delete_state(chat_id)
                    return
                
                data['product_id'] = product['id'] # የተመለሰውን UUID ማስቀመጥ
            
            bot.send_message(chat_id, "📐 አሁን ለጫማው ዝርዝር መረጃዎችን እናስገባ።\nየመጀመሪያውን የጫማ መጠን ቁጥር (Size) ያስገቡ (ከ 30 እስከ 50 መካከል)፦")
            bot.set_state(chat_id, AddProductStates.waiting_for_variant_size)
            
        except Exception as e:
            logger.error(f"Error in creating base product: {e}")
            try:
                bot.delete_message(chat_id, load_msg.message_id)
            except Exception:
                pass
            bot.send_message(chat_id, "❌ የዳታቤዝ ስህተት አጋጥሟል። እባክዎ የሜዳዎች አወቃቀር (Schema) በትክክል መሆኑን ያረጋግጡ።")
            bot.delete_state(chat_id)
        finally:
            if chat_id in processing_admins:
                processing_admins.remove(chat_id)

    # 🎨 8. የጫማ መጠን ማረጋገጫ እና ቀለም ጥያቄ
    @bot.message_handler(state=AddProductStates.waiting_for_variant_size)
    def process_variant_size(message):
        chat_id = message.chat.id
        size_text = message.text.strip()
        
        if not size_text.isdigit() or int(size_text) < 30 or int(size_text) > 50:
            bot.send_message(chat_id, "⚠️ ስህተት፦ የጫማ መጠን ቁጥር (Size) ከ 30 እስከ 50 መካከል መሆን አለበት፦")
            return
        
        with bot.retrieve_data(chat_id) as data:
            data['variant_size'] = int(size_text)
        
        bot.send_message(chat_id, "🎨 የዚህን መጠን ጫማ ቀለም ያስገቡ (ምሳሌ፦ ጥቁር፣ ነጭ)፦")
        bot.set_state(chat_id, AddProductStates.waiting_for_variant_color)

    # 📦 9. የጫማ ቀለም መቀበያ እና የክምችት (Stock) ብዛት ጥያቄ
    @bot.message_handler(state=AddProductStates.waiting_for_variant_color)
    def process_variant_color(message):
        chat_id = message.chat.id
        color = message.text.strip()
        
        if len(color) < 2 or color.isdigit():
            bot.send_message(chat_id, "⚠️ እባክዎ ትክክለኛ የጫማ ቀለም ስም በፊደላት ብቻ ያስገቡ፦")
            return

        with bot.retrieve_data(chat_id) as data:
            data['variant_color'] = color
        
        bot.send_message(chat_id, f"📦 በዚሁ መጠን እና ቀለም በሱቅ ውስጥ ያለውን አጠቃላይ የጫማ ክምችት ብዛት (Stock) ያስገቡ፦")
        bot.set_state(chat_id, AddProductStates.waiting_for_variant_stock)

    # 📸 10. የክምችት ማረጋገጫ እና የፎቶ ሊንክ ጥያቄ
    @bot.message_handler(state=AddProductStates.waiting_for_variant_stock)
    def process_variant_stock(message):
        chat_id = message.chat.id
        stock_text = message.text.strip()
        
        if not stock_text.isdigit() or int(stock_text) < 0:
            bot.send_message(chat_id, "⚠️ ስህተት፦ እባክዎ የክምችት ብዛትን በፖዘቲቭ ቁጥር ብቻ ያስገቡ፦")
            return
        
        with bot.retrieve_data(chat_id) as data:
            data['variant_stock'] = int(stock_text)
        
        bot.send_message(chat_id, "📸 የጫማውን ፎቶ ሊንክ (Supabase Storage URL) ያስገቡ፣ ፎቶ ከሌለው 'skip' ይጻፉ፦")
        bot.set_state(chat_id, AddProductStates.waiting_for_variant_image)

    # ✨ 11. ፎቶ መቀበያ፣ ዝርዝር መረጃውን በዳታቤዝ መጫኛ እና የማጠቃለያ ምርጫ
    @bot.message_handler(state=AddProductStates.waiting_for_variant_image)
    def process_variant_image(message):
        chat_id = message.chat.id
        image_url_text = message.text.strip()
        image_url = image_url_text if image_url_text.lower() != 'skip' else None
        
        if image_url and not (image_url.startswith('http://') or image_url.startswith('https://')):
            bot.send_message(chat_id, "⚠️ ስህተት፦ እባክዎ ትክክለኛ የፎቶ URL ሊንክ ያስገቡ ወይም 'skip' ይጻፉ፦")
            return

        try:
            with bot.retrieve_data(chat_id) as data:
                # 🔄 በ database.py ላይ ያለውን የ DatabaseManager ዝግጁ ፈንክሽን መጠቀም
                variant = db.db.add_product_variant(
                    product_id=data['product_id'],
                    size=data['variant_size'],
                    color=data['variant_color'],
                    stock=data['variant_stock'],
                    image_url=image_url
                )
                
                if variant:
                    price_display = f"{data['base_price']} ETB"
                    if data.get('original_price'):
                        price_display = f"<s>{data['original_price']}</s> {data['base_price']} ETB"
                    
                    success_text = (
                        f"✅ <b>አዲስ ጫማ በተሳካ ሁኔታ ተመዝግቧል!</b>\n\n"
                        f"👟 <b>ሞዴል ስም:</b> {data['name']}\n"
                        f"🏷️ <b>ብራንድ:</b> {data['brand']}\n"
                        f"🗂️ <b>ምድብ:</b> {data['category']}\n"
                        f"💵 <b>ዋጋ:</b> {price_display}\n"
                        f"📐 <b>የጫማ መጠን (Size):</b> {data['variant_size']}\n"
                        f"🎨 <b>ቀለም:</b> {data['variant_color']}\n"
                        f"📦 <b>የሱቅ ክምችት (Stock):</b> {data['variant_stock']} ጥንድ"
                    )
                    bot.send_message(chat_id, success_text, parse_mode="HTML")
                    
                    markup = InlineKeyboardMarkup()
                    markup.add(
                        InlineKeyboardButton("➕ ሌላ መጠን/ቀለም አክል", callback_data=f"add_more_variants_{data['product_id']}"),
                        InlineKeyboardButton("✅ ጨርሻለሁ", callback_data="finish_product")
                    )
                    bot.send_message(chat_id, "💡 ለዚህ ጫማ ሌላ ተጨማሪ መጠን ወይም ቀለም መጨመር ይፈልጋሉ?", reply_markup=markup)
                else:
                    bot.send_message(chat_id, "❌ ስህተት፦ የጫማውን ዝርዝር መጠን በዳታቤዝ ላይ መጫን አልተሳካም።")
        except Exception as e:
            logger.error(f"Error saving variant: {e}")
            bot.send_message(chat_id, "❌ የዝርዝር መረጃ (Variant) የዳታቤዝ ስህተት አጋጥሟል።")
            
        bot.delete_state(chat_id)

    # ======================================================================
    # ➕ ተጨማሪ የጫማ መጠን እና ቀለም (Variants) የመቀበያ ክፍል
    # ======================================================================
    @bot.callback_query_handler(func=lambda call: call.data.startswith("add_more_variants_"))
    def add_more_variants(call):
        chat_id = call.message.chat.id
        telegram_id = call.from_user.id
        
        if telegram_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ ይህ ተግባር ለእርስዎ አልተፈቀደም!", show_alert=True)
            return
        
        bot.answer_callback_query(call.id)
        bot.delete_state(chat_id)
        
        product_id = call.data.replace("add_more_variants_", "")
        bot.set_state(chat_id, AddVariantStates.waiting_for_size)
        
        with bot.retrieve_data(chat_id) as data:
            data['product_id'] = product_id
        
        bot.send_message(chat_id, "📐 የምትጨምሩትን አዲሱን የጫማ መጠን ቁጥር (Size) ያስገቡ (ከ 30 እስከ 50 መካከል)፦")

    @bot.message_handler(state=AddVariantStates.waiting_for_size)
    def process_new_variant_size(message):
        chat_id = message.chat.id
        size_text = message.text.strip()
        
        if not size_text.isdigit() or int(size_text) < 30 or int(size_text) > 50:
            bot.send_message(chat_id, "⚠️ ስህተት፦ የጫማ መጠን ቁጥር (Size) ከ 30 እስከ 50 መካከል መሆን አለበት፦")
            return
            
        with bot.retrieve_data(chat_id) as data:
            data['variant_size'] = int(size_text)
            
        bot.send_message(chat_id, "🎨 የአዲሱን የጫማ መጠን ቀለም ያስገቡ፦")
        bot.set_state(chat_id, AddVariantStates.waiting_for_color)

    @bot.message_handler(state=AddVariantStates.waiting_for_color)
    def process_new_variant_color(message):
        chat_id = message.chat.id
        color = message.text.strip()
        
        if len(color) < 2 or color.isdigit():
            bot.send_message(chat_id, "⚠️ እባክዎ ትክክለኛ የጫማ ቀለም ስም በፊደላት ብቻ ያስገቡ፦")
            return

        with bot.retrieve_data(chat_id) as data:
            data['variant_color'] = color
            
        bot.send_message(chat_id, "📦 የዚህን መጠን አጠቃላይ የጫማ ክምችት ብዛት (Stock) ያስገቡ፦")
        bot.set_state(chat_id, AddVariantStates.waiting_for_stock)

    @bot.message_handler(state=AddVariantStates.waiting_for_stock)
    def process_new_variant_stock(message):
        chat_id = message.chat.id
        stock_text = message.text.strip()
        
        if not stock_text.isdigit() or int(stock_text) < 0:
            bot.send_message(chat_id, "⚠️ ስህተት፦ እባክዎ የክምችት ብዛትን በቁጥር ብቻ ያስገቡ፦")
            return
            
        with bot.retrieve_data(chat_id) as data:
            data['variant_stock'] = int(stock_text)
            
        bot.send_message(chat_id, "📸 የዚህን መጠን ጫማ ፎቶ ሊንክ ያስገቡ ወይም 'skip' ይጻፉ፦")
        bot.set_state(chat_id, AddVariantStates.waiting_for_image)

    @bot.message_handler(state=AddVariantStates.waiting_for_image)
    def process_new_variant_image(message):
        chat_id = message.chat.id
        image_url_text = message.text.strip()
        image_url = image_url_text if image_url_text.lower() != 'skip' else None
        
        if image_url and not (image_url.startswith('http://') or image_url.startswith('https://')):
            bot.send_message(chat_id, "⚠️ ስህተት፦ እባክዎ ትክክለኛ የፎቶ URL ሊንክ ያስገቡ ወይም 'skip' ይጻፉ፦")
            return

        try:
            with bot.retrieve_data(chat_id) as data:
                # 🔄 በ database.py ላይ ያለውን የ DatabaseManager ዝግጁ ፈንክሽን መጠቀም
                variant = db.db.add_product_variant(
                    product_id=data['product_id'],
                    size=data['variant_size'],
                    color=data['variant_color'],
                    stock=data['variant_stock'],
                    image_url=image_url
                )
                
                if variant:
                    success_text = (
                        f"✅ <b>ተጨማሪ የጫማ ዝርዝር በተሳካ ሁኔታ ተቀምጧል!</b>\n\n"
                        f"📐 <b>መጠን (Size):</b> {data['variant_size']}\n"
                        f"🎨 <b>ቀለም:</b> {data['variant_color']}\n"
                        f"📦 <b>ክምችት:</b> {data['variant_stock']} ጥንድ"
                    )
                    bot.send_message(chat_id, success_text, parse_mode="HTML")
                    
                    markup = InlineKeyboardMarkup()
                    markup.add(
                        InlineKeyboardButton("➕ ሌላ መጠን/ቀለም አክል", callback_data=f"add_more_variants_{data['product_id']}"),
                        InlineKeyboardButton("✅ ጨርሻለሁ", callback_data="finish_product")
                    )
                    bot.send_message(chat_id, "💡 ለዚህ ጫማ ሌላ ተጨማሪ መጠን ወይም ቀለም መጨመር ይፈልጋሉ?", reply_markup=markup)
                else:
                    bot.send_message(chat_id, "❌ ስህተት፦ ተጨማሪ የጫማ መጠን ማከል አልተሳካም።")
        except Exception as e:
            logger.error(f"Error adding variant: {e}")
            bot.send_message(chat_id, "❌ ተጨማሪ ዝርዝር ሲመዘገብ የዳታቤዝ ስህተት አጋጥሟል።")
                
        bot.delete_state(chat_id)

    # 🏁 12. ሁሉንም ጨርሶ ወደ ዋናው መስመር መመለሻ
    @bot.callback_query_handler(func=lambda call: call.data == "finish_product")
    def finish_product(call):
        chat_id = call.message.chat.id
        bot.answer_callback_query(call.id, "✅ ምዝገባው ተጠናቋል!")
        bot.delete_state(chat_id)
        bot.send_message(chat_id, "👌 የጫማው ሞዴል እና ዝርዝር መጠኖቹ ሙሉ በሙሉ በዳታቤዝ ውስጥ ተቀምጠው አልቀዋል። አሁን አድሚን ፓነልን መጠቀም ይችላሉ።")