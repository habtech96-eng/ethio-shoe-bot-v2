"""
Admin handlers for Ethiopian Shoe Store
Full CRUD operations for products, variants, orders, and payments
"""
import telebot
from telebot.handler_backends import State, StatesGroup
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import ADMIN_IDS
from backend.database import db
import logging

logger = logging.getLogger(__name__)

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
    
    # Admin panel main menu
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
        
        # Send category selection
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("👞 የወንዶች", callback_data="cat_የወንዶች"),
            InlineKeyboardButton("👠 የሴቶች", callback_data="cat_የሴቶች"),
            InlineKeyboardButton(" 👟 የህፃናት", callback_data="cat_የህፃናት"),
            InlineKeyboardButton("👥 Unisex", callback_data="cat_የሁለቱም/Unisex")
        )
        bot.send_message(chat_id, "🗂️ የምርት ምድብ ይምረጡ፦", reply_markup=markup)
        bot.set_state(chat_id, AddProductStates.waiting_for_category)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("cat_"), state=AddProductStates.waiting_for_category)
    def process_category(call):
        chat_id = call.message.chat.id
        category = call.data.replace("cat_", "")
        bot.answer_callback_query(call.id)
        
        with bot.retrieve_data(chat_id) as data:
            data['category'] = category
        
        # Send brand selection
        markup = InlineKeyboardMarkup(row_width=2)
        markup.add(
            InlineKeyboardButton("Nike", callback_data="brand_Nike"),
            InlineKeyboardButton("Adidas", callback_data="brand_Adidas"),
            InlineKeyboardButton("Puma", callback_data="brand_Puma"),
            InlineKeyboardButton("Reebok", callback_data="brand_Reebok"),
            InlineKeyboardButton("Jordan", callback_data="brand_Jordan"),
            InlineKeyboardButton("Local", callback_data="brand_Local"),
            InlineKeyboardButton("Other", callback_data="brand_Other")
        )
        bot.send_message(chat_id, "🏷️ የምርቱን የምርት ስም (Brand) ይምረጡ፦", reply_markup=markup)
        bot.set_state(chat_id, AddProductStates.waiting_for_brand)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("brand_"), state=AddProductStates.waiting_for_brand)
    def process_brand(call):
        chat_id = call.message.chat.id
        brand = call.data.replace("brand_", "")
        bot.answer_callback_query(call.id)
        
        with bot.retrieve_data(chat_id) as data:
            data['brand'] = brand
        
        bot.send_message(chat_id, "💵 የምርቱን መሰረታዊ ዋጋ በ ETB ብቻ ያስገቡ (ምሳሌ፦ 2500)፦")
        bot.set_state(chat_id, AddProductStates.waiting_for_price)

    @bot.message_handler(state=AddProductStates.waiting_for_price)
    def process_price(message):
        chat_id = message.chat.id
        price_text = message.text.strip()
        
        if not price_text.isdigit() or int(price_text) < 0:
            bot.send_message(chat_id, "⚠️ እባክህ ዋጋውን በቁጥር ብቻ አስገባ፦")
            return
        
        with bot.retrieve_data(chat_id) as data:
            data['base_price'] = int(price_text)
        
        bot.send_message(chat_id, "💰 የኦሪጅናል ዋጋ (Original Price) ለቅናሽ ማሳያ፣ ወይም 0 ያስገቡ፦")
        bot.set_state(chat_id, AddProductStates.waiting_for_original_price)

    @bot.message_handler(state=AddProductStates.waiting_for_original_price)
    def process_original_price(message):
        chat_id = message.chat.id
        original_text = message.text.strip()
        
        if not original_text.isdigit():
            bot.send_message(chat_id, "⚠️ እባክህ ዋጋውን በቁጥር ብቻ አስገባ፦")
            return
        
        with bot.retrieve_data(chat_id) as data:
            original_price = int(original_text) if int(original_text) > 0 else None
            data['original_price'] = original_price
        
        bot.send_message(chat_id, "📝 የምርቱ መግለጫ (Description) ያስገቡ ወይም 'skip' ይጻፉ፦")
        bot.set_state(chat_id, AddProductStates.waiting_for_description)

    @bot.message_handler(state=AddProductStates.waiting_for_description)
    def process_description(message):
        chat_id = message.chat.id
        description = message.text.strip() if message.text.strip().lower() != 'skip' else None
        
        with bot.retrieve_data(chat_id) as data:
            data['description'] = description
            
            # Create the product in database
            product = db.add_product(
                name=data['name'],
                category=data['category'],
                base_price=data['base_price'],
                description=description,
                brand=data['brand'],
                original_price=data.get('original_price')
            )
            
            if not product:
                bot.send_message(chat_id, "❌ ምርት ማከል አልተሳካም።")
                bot.delete_state(chat_id)
                return
            
            data['product_id'] = product['id']
        
        # Ask for variant information
        bot.send_message(chat_id, "📐 የመጀመሪያውን variant ሳይዝ ያስገባ (35-50)፦")
        bot.set_state(chat_id, AddProductStates.waiting_for_variant_size)

    @bot.message_handler(state=AddProductStates.waiting_for_variant_size)
    def process_variant_size(message):
        chat_id = message.chat.id
        size_text = message.text.strip()
        
        if not size_text.isdigit() or int(size_text) < 30 or int(size_text) > 50:
            bot.send_message(chat_id, "⚠️ ሳይዝ ከ 30 እስከ 50 መካከል መሆን አለበት፦")
            return
        
        with bot.retrieve_data(chat_id) as data:
            data['variant_size'] = int(size_text)
        
        bot.send_message(chat_id, "🎨 የቬሪያንቱን ቀለም (Color) ያስገባ፦")
        bot.set_state(chat_id, AddProductStates.waiting_for_variant_color)

    @bot.message_handler(state=AddProductStates.waiting_for_variant_color)
    def process_variant_color(message):
        chat_id = message.chat.id
        color = message.text.strip()
        
        with bot.retrieve_data(chat_id) as data:
            data['variant_color'] = color
        
        bot.send_message(chat_id, "📦 የስቶክ ብዛት (Stock) ያስገባ፦")
        bot.set_state(chat_id, AddProductStates.waiting_for_variant_stock)

    @bot.message_handler(state=AddProductStates.waiting_for_variant_stock)
    def process_variant_stock(message):
        chat_id = message.chat.id
        stock_text = message.text.strip()
        
        if not stock_text.isdigit() or int(stock_text) < 0:
            bot.send_message(chat_id, "⚠️ እባክህ ስቶክ ቁጥር በትክክል አስገባ፦")
            return
        
        with bot.retrieve_data(chat_id) as data:
            data['variant_stock'] = int(stock_text)
        
        bot.send_message(chat_id, "📸 የቬሪያንቱን ፎቶ URL ያስገባ ወይም 'skip' ይጻፉ፦")
        bot.set_state(chat_id, AddProductStates.waiting_for_variant_image)

    @bot.message_handler(state=AddProductStates.waiting_for_variant_image)
    def process_variant_image(message):
        chat_id = message.chat.id
        image_url = message.text.strip() if message.text.strip().lower() != 'skip' else None
        
        with bot.retrieve_data(chat_id) as data:
            # Add the variant to database
            variant = db.add_product_variant(
                product_id=data['product_id'],
                size=data['variant_size'],
                color=data['variant_color'],
                stock=data['variant_stock'],
                image_url=image_url
            )
            
            if variant:
                product_name = data['name']
                category = data['category']
                brand = data['brand']
                base_price = data['base_price']
                original_price = data.get('original_price')
                
                price_display = f"{base_price} ETB (ብር)"
                if original_price:
                    price_display = f"~~{original_price}~~ {base_price} ETB (ብር)"
                
                success_text = (
                    f"✅ **ምርቱ በተሳካ ሁኔታ ተቀምጧል!**\n\n"
                    f"👟 **ስም:** {product_name}\n"
                    f"🏷️ **ምርት ስም:** {brand}\n"
                    f"🗂️ **ምድብ:** {category}\n"
                    f"💵 **ዋጋ:** {price_display}\n"
                    f"📐 **ሳይዝ:** {data['variant_size']}\n"
                    f"🎨 **ቀለም:** {data['variant_color']}\n"
                    f"📦 **ስቶክ:** {data['variant_stock']}"
                )
                bot.send_message(chat_id, success_text, parse_mode="Markdown")
                
                # Ask if they want to add more variants
                markup = InlineKeyboardMarkup()
                markup.add(
                    InlineKeyboardButton("➕ ተጨማሪ Variant አክል", callback_data=f"add_more_variants_{data['product_id']}"),
                    InlineKeyboardButton("✅ ጨርሻለሁ", callback_data="finish_product")
                )
                bot.send_message(chat_id, "ተጨማሪ variants መጨመር ይፈልጋሉ?", reply_markup=markup)
            else:
                bot.send_message(chat_id, "❌ Variant ማከል አልተሳካም።")
        
        bot.delete_state(chat_id)

    # ----------------------------------------------------------------------
    # 🛠️ አዲስ የተጨመሩ የ "ተጨማሪ Variant" መቀበያ ፈንክሽኖች (Fixed Section)
    # ----------------------------------------------------------------------
    @bot.callback_query_handler(func=lambda call: call.data.startswith("add_more_variants_"))
    def add_more_variants(call):
        chat_id = call.message.chat.id
        if chat_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ ይህ እርምጃ ለእርስዎ አልተፈቀደም!", show_alert=True)
            return
        
        bot.answer_callback_query(call.id)
        product_id = call.data.replace("add_more_variants_", "")
        
        bot.set_state(chat_id, AddVariantStates.waiting_for_size)
        with bot.retrieve_data(chat_id) as data:
            data['product_id'] = product_id
        
        bot.send_message(chat_id, "📐 የአዲሱን variant ሳይዝ ያስገቡ (35-50)፦")

    @bot.message_handler(state=AddVariantStates.waiting_for_size)
    def process_new_variant_size(message):
        chat_id = message.chat.id
        size_text = message.text.strip()
        
        if not size_text.isdigit() or int(size_text) < 30 or int(size_text) > 50:
            bot.send_message(chat_id, "⚠️ ሳይዝ ከ 30 እስከ 50 መካከል መሆን አለበት፦")
            return
            
        with bot.retrieve_data(chat_id) as data:
            data['variant_size'] = int(size_text)
            
        bot.send_message(chat_id, "🎨 የአዲሱን ቬሪያንት ቀለም (Color) ያስገቡ፦")
        bot.set_state(chat_id, AddVariantStates.waiting_for_color)

    @bot.message_handler(state=AddVariantStates.waiting_for_color)
    def process_new_variant_color(message):
        chat_id = message.chat.id
        color = message.text.strip()
        
        with bot.retrieve_data(chat_id) as data:
            data['variant_color'] = color
            
        bot.send_message(chat_id, "📦 የአዲሱን ቬሪያንት የስቶክ ብዛት (Stock) ያስገቡ፦")
        bot.set_state(chat_id, AddVariantStates.waiting_for_stock)

    @bot.message_handler(state=AddVariantStates.waiting_for_stock)
    def process_new_variant_stock(message):
        chat_id = message.chat.id
        stock_text = message.text.strip()
        
        if not stock_text.isdigit() or int(stock_text) < 0:
            bot.send_message(chat_id, "⚠️ እባክህ ስቶክ ቁጥር በትክክል አስገባ፦")
            return
            
        with bot.retrieve_data(chat_id) as data:
            data['variant_stock'] = int(stock_text)
            
        bot.send_message(chat_id, "📸 የአዲሱን ቬሪያንት ፎቶ URL ያስገቡ ወይም 'skip' ይጻፉ፦")
        bot.set_state(chat_id, AddVariantStates.waiting_for_image)

    @bot.message_handler(state=AddVariantStates.waiting_for_image)
    def process_new_variant_image(message):
        chat_id = message.chat.id
        image_url = message.text.strip() if message.text.strip().lower() != 'skip' else None
        
        with bot.retrieve_data(chat_id) as data:
            # በዳታቤዝ ውስጥ ማስቀመጥ
            variant = db.add_product_variant(
                product_id=data['product_id'],
                size=data['variant_size'],
                color=data['variant_color'],
                stock=data['variant_stock'],
                image_url=image_url
            )
            
            if variant:
                success_text = (
                    f"✅ **추가 ተጨማሪ Variant በተሳካ ሁኔታ ተቀምጧል!**\n\n"
                    f"📐 **ሳይዝ:** {data['variant_size']}\n"
                    f"🎨 **ቀለም:** {data['variant_color']}\n"
                    f"📦 **ስቶክ:** {data['variant_stock']}"
                )
                bot.send_message(chat_id, success_text, parse_mode="Markdown")
                
                # እንደገና ምርጫ መስጠት
                markup = InlineKeyboardMarkup()
                markup.add(
                    InlineKeyboardButton("➕ ተጨማሪ Variant አክል", callback_data=f"add_more_variants_{data['product_id']}"),
                    InlineKeyboardButton("✅ ጨርሻለሁ", callback_data="finish_product")
                )
                bot.send_message(chat_id, "ተጨማሪ variants መጨመር ይፈልጋሉ?", reply_markup=markup)
            else:
                bot.send_message(chat_id, "❌ Variant ማከል አልተሳካም።")
                
        bot.delete_state(chat_id)

    @bot.callback_query_handler(func=lambda call: call.data == "finish_product")
    def finish_product(call):
        chat_id = call.message.chat.id
        bot.answer_callback_query(call.id, "✅ ምርት ማከል ተጠናቋል!")
        bot.delete_state(chat_id)
        bot.send_message(chat_id, "👌 ምርቱ ሙሉ በሙሉ ተመዝግቦ ተጠናቋል። ወደ ዋናው ሜኑ መመለስ ይችላሉ።")