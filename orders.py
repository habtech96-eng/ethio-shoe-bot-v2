import telebot
from telebot.handler_backends import State, StatesGroup
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import database
import keyboards
from config import ADMIN_IDS
from receipt import generate_receipt_image
import os

class CustomerOrderStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_location = State()

def register_order_handlers(bot):

    # 🛍️ ደንበኛው "አሁኑኑ እዘዝ" ሲል
    @bot.callback_query_handler(func=lambda call: call.data.startswith("buy_"))
    def start_order_flow(call):
        chat_id = call.message.chat.id
        product_id = call.data.replace("buy_", "")
        bot.answer_callback_query(call.id)
        
        try:
            # ምርቱን ከ Supabase ማውጣት
            res = database.supabase.table('products').select('*, product_variants(*)').eq('id', product_id).execute()
            
            if not res.data:
                bot.send_message(chat_id, "⚠️ ይቅርታ፣ ይህ ምርት በአሁን ሰዓት አልተገኘም።")
                return
                
            product = res.data[0]
            variants = product.get('product_variants', [])
            size = variants[0].get('size', 'N/A') if variants else 'N/A'
            price = product.get('base_price', '0')
            
            bot.set_state(chat_id, CustomerOrderStates.waiting_for_phone)
            with bot.retrieve_data(chat_id) as data:
                data['product_id'] = product['id']
                data['product_name'] = product['name']
                data['price'] = price
                data['size'] = size
                data['customer_name'] = f"{call.from_user.first_name or ''} {call.from_user.last_name or ''}".strip()
                
            bot.send_message(
                chat_id, 
                "📱 ትዕዛዝዎን ለመመዝገብ ከታች ያለውን **'ስልኬን በራስ-ሰር ላክ'** የሚለውን በተን ይጫኑ፦", 
                reply_markup=keyboards.get_phone_keyboard(),
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Error starting order flow: {e}")
            bot.send_message(chat_id, "⚠️ በትዕዛዝ ሂደት ላይ ስህተት አጋጥሟል። እባክዎ እንደገና ይሞክሩ።")

    # 1️⃣ የስልክ ቁጥር መቀበያ
    @bot.message_handler(state=CustomerOrderStates.waiting_for_phone, content_types=['contact', 'text'])
    def process_customer_phone(message):
        chat_id = message.chat.id
        phone = message.contact.phone_number if message.contact is not None else message.text.strip()
            
        with bot.retrieve_data(chat_id) as data:
            data['phone'] = phone
            
        bot.send_message(
            chat_id, 
            "📍 እቃው የሚረከቡበትን አድራሻ ይምረጡ ወይም ይጻፉ፦", 
            reply_markup=keyboards.get_location_keyboard()
        )
        bot.set_state(chat_id, CustomerOrderStates.waiting_for_location)

    # 2️⃣ የአድራሻ መቀበያ እና ትዕዛዝ በ Supabase መመዝገቢያ
    @bot.message_handler(state=CustomerOrderStates.waiting_for_location)
    def process_customer_location(message):
        chat_id = message.chat.id
        location = message.text.strip()
        
        try:
            with bot.retrieve_data(chat_id) as data:
                product_name = data['product_name']
                customer_name = data['customer_name']
                phone = data['phone']
                price = data['price']
                size = data['size']
                
                # ሀ. ደንበኛው በ Supabase 'users' ሰንጠረዥ ውስጥ መኖሩን ማረጋገጥ/መመዝገብ
                user_res = database.supabase.table('users').select('id').eq('telegram_id', chat_id).execute()
                if user_res.data:
                    user_uuid = user_res.data[0]['id']
                else:
                    new_user = database.supabase.table('users').insert({
                        'telegram_id': chat_id,
                        'first_name': message.from_user.first_name or "Customer",
                        'last_name': message.from_user.last_name or ""
                    }).execute()
                    user_uuid = new_user.data[0]['id']
                
                # ለ. ትዕዛዙን በ Supabase 'orders' ሰንጠረዥ ውስጥ መመዝገብ
                order_res = database.supabase.table('orders').insert({
                    'user_id': user_uuid,
                    'contact_phone': phone,
                    'order_status': '⏱️ ይጠበቃል',
                    'delivery_address': location,
                    'product_name': product_name, # በሰንጠረዡ መዋቅር መሰረት
                    'price': str(price),
                    'size': str(size)
                }).execute()
                
                order_uuid = order_res.data[0]['id']
                short_order_id = order_uuid[:8] # ለአጭር ማሳያ
                
            bot.delete_state(chat_id)
            
            success_msg = (
                f"🎉 **ትዕዛዝዎ በተሳካ ሁኔታ ተመዝግቧል!**\n\n"
                f"🆔 **የትዕዛዝ ቁጥር፦** #{short_order_id}\n"
                f"👟 **የጫማ ሞዴል፦** {product_name} (Size: {size})\n"
                f"💰 **ዋጋ፦** {price} ETB\n"
                f"📍 **አድራሻ፦** {location}\n\n"
                f"⏳ **ቀጣይ ደረጃ፦** አድሚኑ ትዕዛዝዎን አይቶ የክፍያ መረጃ ይልክልዎታል። እባክዎ በትዕግስት ይጠብቁ!"
            )
            bot.send_message(chat_id, success_msg, parse_mode="Markdown", reply_markup=keyboards.get_main_menu())
            
            # ለአድሚን የሚላክ ማሳወቂያ (የቴሌግራም 64-byte ሊሚትን ለመጠበቅ UUID ውን ብቻ እናስተላልፋለን)
            admin_markup = InlineKeyboardMarkup()
            admin_markup.row(
                InlineKeyboardButton("💳 Send Payment Info", callback_data=f"sp_{order_uuid}_{price}_{size}"),
                InlineKeyboardButton("❌ Reject Order", callback_data=f"rj_{order_uuid}")
            )
            
            admin_alert = (
                f"⚠️ **አዲስ ትዕዛዝ ገብቷል!**\n\n"
                f"🆔 **የትዕዛዝ ቁጥር፦** #{short_order_id}\n"
                f"👤 **ደንበኛ፦** {customer_name}\n"
                f"👟 **ምርት፦** {product_name} (Size: {size})\n"
                f"📞 **ስልክ፦** {phone}\n"
                f"📍 **አድራሻ፦** {location}\n"
                f"💵 **ክፍያ፦** {price} ETB\n\n"
                f"👉 ትዕዛዙን ተቀብለው ለደንበኛው የባንክ አካውንት ለመላክ **Send Payment Info** የሚለውን ይጫኑ።"
            )
            
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(admin_id, admin_alert, parse_mode="Markdown", reply_markup=admin_markup)
                except Exception as e:
                    print(f"Admin Notify Error: {e}")
                    
        except Exception as main_err:
            print(f"Critical Insertion Error: {main_err}")
            bot.send_message(chat_id, "⚠️ ትዕዛዝዎን መመዝገብ አልተቻለም። እባክዎ እንደገና ይሞክሩ።")

    # 3️⃣ 🎯 የደረጃ በደረጃ በይነገጽ (Interaction Logic ከ Supabase ጋር)
    @bot.callback_query_handler(func=lambda call: any(call.data.startswith(prefix) for prefix in ["sp_", "paid_", "fa_", "rj_"]))
    def handle_interactive_workflow(call):
        try:
            bot.answer_callback_query(call.id)
            action_data = call.data.split("_")
            action = action_data[0]
            order_uuid = action_data[1]
            short_id = order_uuid[:8]
            
            # መረጃውን ከ Supabase መውሰድ
            res = database.supabase.table('orders').select('*, users(*)').eq('id', order_uuid).execute()
            
            if not res.data:
                bot.send_message(call.message.chat.id, "⚠️ ስህተት፦ ይህ ትዕዛዝ በዳታቤዝ ውስጥ አልተገኘም።")
                return
                
            order = res.data[0]
            user_chat_id = order['users']['telegram_id'] if order.get('users') else call.message.chat.id
            user_name = order['users']['first_name'] if order.get('users') else "Customer"
            product_name = order.get('product_name', 'ጫማ')
            phone = order.get('contact_phone', '')
            
            price = action_data[2] if len(action_data) > 2 else "3000"
            size = action_data[3] if len(action_data) > 3 else "41"

            # -------------------------------------------------------------
            # STEP A: አድሚኑ "Send Payment Info" ሲጫን
            # -------------------------------------------------------------
            if action == "sp":
                database.supabase.table('orders').update({'order_status': '💳 ክፍያ ይጠበቃል'}).eq('id', order_uuid).execute()
                bot.edit_message_text(f"⏳ ለትዕዛዝ #{short_id} የክፍያ መረጃ ለደንበኛው ተልኳል። ደንበኛው ክፍያ እስኪፈጽም ይጠበቃል።", call.message.chat.id, call.message.message_id)
                
                pay_markup = InlineKeyboardMarkup()
                pay_markup.add(InlineKeyboardButton("✅ ክፍያ ፈጽሜያለሁ / I have Paid", callback_data=f"paid_{order_uuid}_{price}_{size}"))
                
                payment_details = (
                    f"💳 **የትዕዛዝ ቁጥር #{short_id} የክፍያ መረጃ**\n\n"
                    f"💵 **ጠቅላላ የሚከፈል፦** {price} ETB\n\n"
                    f"📌 **የባንክ አካውንቶች፦**\n"
                    f"• ንግድ ባንክ (CBE)፦ `1000274286637`\n"
                    f"• አቢሲኒያ ባንክ፦ `150662915`\n"
                    f"• Telebirr፦ `0938649925`\n\n"
                    f"👉 ክፍያውን እንደፈጸሙ የከፈሉበትን ደረሰኝ (Screenshot) ለባለቤቱ [@hab7tech] ይላኩ። "
                    f"ከዚያም ከታች ያለውን **'ክፍያ ፈጽሜያለሁ'** የሚለውን በተን መጫን እንዳይረሱ! 👇"
                )
                bot.send_message(user_chat_id, payment_details, parse_mode="Markdown", reply_markup=pay_markup)

            # -------------------------------------------------------------
            # STEP B: ደንበኛው "ክፍያ ፈጽሜያለሁ" ሲል
            # -------------------------------------------------------------
            elif action == "paid":
                database.supabase.table('orders').update({'order_status': '⏳ ማረጋገጫ ላይ'}).eq('id', order_uuid).execute()
                bot.edit_message_text(f"⏳ ማሳወቂያዎ ለአድሚን ደርሷል። ክፍያዎ ተረጋግጦ የመጨረሻው ዲጂታል ደረሰኝ በቅርቡ ይላክለታል።", call.message.chat.id, call.message.message_id)
                
                confirm_markup = InlineKeyboardMarkup()
                confirm_markup.row(
                    InlineKeyboardButton("✅ Approve Payment & Send Receipt", callback_data=f"fa_{order_uuid}_{price}_{size}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"rj_{order_uuid}")
                )
                
                for admin_id in ADMIN_IDS:
                    try:
                        bot.send_message(
                            admin_id, 
                            f"💰 **የክፍያ ማሳወቂያ (ትዕዛዝ #{short_id})!**\n\nደንበኛው **{user_name}** ክፍያ መፈጸሙን አሳውቋል። እባክዎ ባንክዎን ያረጋግጡና ክፍያው ከገባ **Approve Payment** የሚለውን ይጫኑ።",
                            reply_markup=confirm_markup
                        )
                    except Exception as e:
                        print(f"Admin Notify Paid Error: {e}")

            # -------------------------------------------------------------
            # STEP C: አድሚኑ "Approve Payment" ሲል (የዲጂታል ደረሰኝ መላኪያ)
            # -------------------------------------------------------------
            elif action == "fa":
                database.supabase.table('orders').update({'order_status': '✅ ተጠናቋል'}).eq('id', order_uuid).execute()
                bot.edit_message_text(f"✅ ለትዕዛዝ #{short_id} ክፍያው ጽድቋል! ኦፊሴላዊ የሽያጭ ማረጋገጫ ደረሰኝ ለደንበኛው ተልኳል።", call.message.chat.id, call.message.message_id)
                bot.send_message(user_chat_id, f"🎉 **ክፍያዎ ተረጋግጧል!**\nየትዕዛዝ ቁጥር #{short_id} ሙሉ በሙሉ ተጠናቋል።")
                
                try:
                    # ደረሰኝ ላይ ረዥም UUID ከሚቀመጥ አጭሩን ID እንዲጠቀም ተደርጓል
                    receipt_file = generate_receipt_image(short_id, user_name, product_name, price, size, phone)
                    with open(receipt_file, 'rb') as photo:
                        bot.send_photo(
                            chat_id=user_chat_id, 
                            photo=photo, 
                            caption=f"🧾 **ኦፊሴላዊ የክፍያ ማረጋገጫ ደረሰኝ (Official Payment Receipt)**\n\nስለ ክፍያዎ እና ስለ እምነትዎ እጅግ እናመሰግናለን! ምርትዎ በቅርቡ አድራሻዎ ላይ ይደርሳል።"
                        )
                    if os.path.exists(receipt_file):
                        os.remove(receipt_file)
                except Exception as e:
                    print(f"Receipt Generation Error: {e}")
                    bot.send_message(user_chat_id, "⚠️ ደረሰኝ ማመንጨት ላይ ስህተት አጋጥሟል፣ ነገር ግን ክፍያዎ ተረጋግጧል።")

            # -------------------------------------------------------------
            # STEP D: አድሚኑ ውድቅ (Reject) ሲያደርግ
            # -------------------------------------------------------------
            elif action == "rj":
                database.supabase.table('orders').update({'order_status': '❌ ተሰርዟል'}).eq('id', order_uuid).execute()
                bot.edit_message_text(f"❌ ትዕዛዝ #{short_id} ውድቅ ተደርጓል።", call.message.chat.id, call.message.message_id)
                bot.send_message(user_chat_id, f"❌ **ይቅርታ፦** የትዕዛዝ ቁጥር #{short_id} በአድሚኑ ውድቅ ተደርጓል (ተሰርዟል)።")
                
        except Exception as main_err:
            print(f"Critical Workflow Error: {main_err}")