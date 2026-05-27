"""
Order management handlers for Ethiopian Shoe Store
Complete order workflow with payment verification
"""
import telebot
from telebot.handler_backends import State, StatesGroup
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from backend.database import db
from config import ADMIN_IDS
from receipt import generate_receipt_image
import os
import logging

logger = logging.getLogger(__name__)

class CustomerOrderStates(StatesGroup):
    waiting_for_phone = State()
    waiting_for_address_selection = State()
    waiting_for_new_address = State()
    waiting_for_payment_method = State()
    waiting_for_transaction_ref = State()

def register_order_handlers(bot):

    # Start order flow from product variant
    @bot.callback_query_handler(func=lambda call: call.data.startswith("order_variant_"))
    def start_order_flow(call):
        chat_id = call.message.chat.id
        telegram_id = call.from_user.id
        variant_id = call.data.replace("order_variant_", "")
        bot.answer_callback_query(call.id)
        
        # Get or create user safely
        user = db.get_user(telegram_id)
        if not user:
            user = db.create_user(telegram_id, call.from_user.first_name, call.from_user.username)
            if not user:
                bot.send_message(chat_id, "❌ ስህተት። እባክዎ ደግመው ይሞክሩ።")
                return
        
        # Get variant details
        variant = db.get_variant(variant_id)
        if not variant:
            bot.send_message(chat_id, "❌ ምርቱ አልተገኘም።")
            return
        
        product = variant.get('products')
        if not product or variant.get('stock', 0) <= 0:
            bot.send_message(chat_id, "⚠️ ይህ ምርት አሁን በስቶክ ውስጥ የለም።")
            return
        
        # Set order state & populate context storage
        bot.set_state(chat_id, CustomerOrderStates.waiting_for_phone)
        with bot.retrieve_data(chat_id) as data:
            data['user_id'] = user['id']
            data['variant_id'] = variant_id
            data['product_name'] = product['name']
            data['size'] = variant['size']
            data['color'] = variant['color']
            data['price_per_unit'] = product['base_price']
            data['customer_name'] = f"{call.from_user.first_name or ''} {call.from_user.last_name or ''}".strip()
        
        # Request phone number
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("📱 ስልኬን በራስ-ሰር ላክ", callback_data="share_phone")
        )
        bot.send_message(
            chat_id,
            "📱 የስልክ ቁጥርዎን ያጋሩ፦",
            reply_markup=markup
        )

    @bot.callback_query_handler(func=lambda call: call.data == "share_phone")
    def request_phone_contact(call):
        chat_id = call.message.chat.id
        bot.answer_callback_query(call.id)
        
        # Send native contact request via reply keyboard
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(telebot.types.KeyboardButton("📱 ስልኬን በራስ-ሰር ላክ", request_contact=True))
        bot.send_message(chat_id, "📱 ስልክ ቁጥርዎን በተን ይጫኑ፦", reply_markup=markup)

    @bot.message_handler(state=CustomerOrderStates.waiting_for_phone, content_types=['contact', 'text'])
    def process_phone(message):
        chat_id = message.chat.id
        phone = message.contact.phone_number if message.contact else message.text.strip()
        
        with bot.retrieve_data(chat_id) as data:
            data['phone'] = phone
            user_id = data['user_id']
        
        # Check existing user addresses
        addresses = db.get_user_addresses(user_id)
        
        if addresses:
            markup = InlineKeyboardMarkup(row_width=1)
            for addr in addresses:
                location_text = f"{addr['city']} - {addr.get('subcity_or_zone', '')} {addr.get('specific_location_or_woreda', '')}"
                markup.add(InlineKeyboardButton(f"📍 {location_text}", callback_data=f"addr_{addr['id']}"))
            markup.add(InlineKeyboardButton("➕ አዲስ አድራሻ አክል", callback_data="new_address"))
            
            bot.send_message(chat_id, "📍 የአድራሻ ምርጫ ይምረጡ፦", reply_markup=markup)
            bot.set_state(chat_id, CustomerOrderStates.waiting_for_address_selection)
        else:
            bot.send_message(chat_id, "📍 አዲስ አድራሻ ያስገቡ፦\n\nምሳሌ፦ Addis Ababa, Bole, Woreda 03")
            bot.set_state(chat_id, CustomerOrderStates.waiting_for_new_address)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("addr_"), state=CustomerOrderStates.waiting_for_address_selection)
    def use_existing_address(call):
        chat_id = call.message.chat.id
        address_id = call.data.replace("addr_", "")
        bot.answer_callback_query(call.id)
        
        with bot.retrieve_data(chat_id) as data:
            data['address_id'] = address_id
        
        show_payment_method_selection(bot, chat_id)

    @bot.callback_query_handler(func=lambda call: call.data == "new_address", state=CustomerOrderStates.waiting_for_address_selection)
    def request_new_address(call):
        chat_id = call.message.chat.id
        bot.answer_callback_query(call.id)
        
        bot.send_message(chat_id, "📍 አዲስ አድራሻ ያስገባ፦\n\nምሳሌ፦ Addis Ababa, Bole, Woreda 03")
        bot.set_state(chat_id, CustomerOrderStates.waiting_for_new_address)

    @bot.message_handler(state=CustomerOrderStates.waiting_for_new_address)
    def process_new_address(message):
        chat_id = message.chat.id
        address_text = message.text.strip()
        
        # Robust parsing step fallback if comma placement is ignored
        if ',' in address_text:
            parts = address_text.split(',')
            city = parts[0].strip()
            subcity = parts[1].strip() if len(parts) > 1 else ""
            specific = parts[2].strip() if len(parts) > 2 else ""
        else:
            # Fallback allocation logic if commas are missing
            city = "Addis Ababa"
            subcity = address_text
            specific = ""
        
        with bot.retrieve_data(chat_id) as data:
            address = db.add_address(
                user_id=data['user_id'],
                city=city,
                subcity_or_zone=subcity,
                specific_location=specific,
                is_default=False
            )
            
            if address:
                data['address_id'] = address['id']
        
        show_payment_method_selection(bot, chat_id)

    def show_payment_method_selection(bot, chat_id):
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("📱 Telebirr", callback_data="pay_telebirr"),
            InlineKeyboardButton("🏦 CBE (ንግድ ባንክ)", callback_data="pay_cbe")
        )
        bot.send_message(chat_id, "💳 የክፍያ ዘዴ ይምረጡ፦", reply_markup=markup)
        bot.set_state(chat_id, CustomerOrderStates.waiting_for_payment_method)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"), state=CustomerOrderStates.waiting_for_payment_method)
    def select_payment_method(call):
        chat_id = call.message.chat.id
        payment_method = call.data.replace("pay_", "")
        bot.answer_callback_query(call.id)
        
        with bot.retrieve_data(chat_id) as data:
            data['payment_method'] = payment_method
            price_per_unit = data['price_per_unit']
            
            subtotal = price_per_unit
            delivery_fee = 50  
            total = subtotal + delivery_fee
            
            data['subtotal'] = subtotal
            data['delivery_fee'] = delivery_fee
            data['total'] = total
        
        payment_info = (
            f"💳 **የክፍያ መረጃ**\n\n"
            f"👟 **ምርት:** {data['product_name']}\n"
            f"📐 **Size:** {data['size']}\n"
            f"🎨 **Color:** {data['color']}\n"
            f"💵 **ዋጋ:** {subtotal} ETB\n"
            f"🚚 **የመጓጓዣ ክፍያ:** {delivery_fee} ETB\n"
            f"💰 **ጠቅላላ:** {total} ETB\n\n"
        )
        
        if payment_method == "telebirr":
            payment_info += (
                f"📱 **Telebirr Payment**\n"
                f"Phone: `0938649925`\n\n"
                f"ክፍያውን ከፈጸሙ በኋላ የማረጋገጫ ኮዱን (Reference) ያስገቡ፦"
            )
        else:
            payment_info += (
                f"🏦 **CBE Bank Payment**\n"
                f"Account: `1000274286637`\n\n"
                f"ክፍያውን ከፈጸሙ በኋላ የማረጋገጫ ኮዱን (Reference) ያስገባ፦"
            )
        
        bot.send_message(chat_id, payment_info, parse_mode="Markdown")
        bot.set_state(chat_id, CustomerOrderStates.waiting_for_transaction_ref)

    @bot.message_handler(state=CustomerOrderStates.waiting_for_transaction_ref)
    def process_transaction_ref(message):
        chat_id = message.chat.id
        transaction_ref = message.text.strip()
        
        with bot.retrieve_data(chat_id) as data:
            items = [{
                'product_name': data['product_name'],
                'size': data['size'],
                'color': data['color'],
                'quantity': 1,
                'price_per_unit': data['price_per_unit']
            }]
            
            order = db.create_order(
                user_id=data['user_id'],
                items=items,
                subtotal=data['subtotal'],
                delivery_fee=data['delivery_fee'],
                discount_amount=0,
                total_amount=data['total'],
                shipping_address_id=data['address_id'],
                contact_phone=data['phone'],
                promo_code_id=None
            )
            
            if not order:
                bot.send_message(chat_id, "❌ ትዕዛዝ መፍጠር አልተሳካም።")
                bot.delete_state(chat_id)
                return
            
            payment = db.create_payment(
                order_id=order['id'],
                payment_method=data['payment_method'],
                transaction_reference=transaction_ref
            )
            
            if payment:
                success_msg = (
                    f"✅ **ትዕዛዝዎ በተሳካ ሁኔታ ተመዝግቧል!**\n\n"
                    f"🆔 **Order ID:** #{order['id'][:8]}\n"
                    f"👟 **ምርት:** {data['product_name']}\n"
                    f"💰 **ጠቅላላ:** {data['total']} ETB\n\n"
                    f"⏳ **መጨረሻ ማረጋገጫ፦** ክፍያዎ ከተረጋገጠ በኋላ ምርትዎ ወዲያውኑ ይላካል።"
                )
                bot.send_message(chat_id, success_msg, parse_mode="Markdown")
                
                # Admin notification context card
                admin_alert = (
                    f"🆕 **አዲስ ትዕዛዝ ገብቷል!**\n\n"
                    f"🆔 Order ID: #{order['id'][:8]}\n"
                    f"👤 Customer: {data['customer_name']}\n"
                    f"📞 Phone: {data['phone']}\n"
                    f"👟 Product: {data['product_name']} (Size {data['size']}, {data['color']})\n"
                    f"💳 Payment: {data['payment_method'].upper()}\n"
                    f"📝 Ref: `{transaction_ref}`\n"
                    f"💰 Total: {data['total']} ETB"
                )
                
                markup = InlineKeyboardMarkup(row_width=2)
                markup.add(
                    InlineKeyboardButton("✅ Verify Payment", callback_data=f"verify_pay_{payment['id']}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"reject_pay_{payment['id']}")
                )
                
                for admin_id in ADMIN_IDS:
                    try:
                        bot.send_message(admin_id, admin_alert, parse_mode="Markdown", reply_markup=markup)
                    except Exception as e:
                        logger.error(f"Error notifying admin {admin_id}: {e}")
            else:
                bot.send_message(chat_id, "❌ የክፍያ መረጃ ማስገባት አልተሳካም።")
            
        bot.delete_state(chat_id)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("verify_pay_"))
    def verify_payment(call):
        admin_user_id = call.from_user.id
        if admin_user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ ይህ እርምጃ ለእርስዎ አልተፈቀደም!", show_alert=True)
            return
        
        payment_id = call.data.replace("verify_pay_", "")
        bot.answer_callback_query(call.id, "✅ Payment Verified!")
        
        payment = db.verify_payment(payment_id, admin_user_id)
        
        if payment:
            db.update_order_status(payment['order_id'], 'confirmed')
            order = db.get_order(payment['order_id'])
            
            if order and order.get('users'):
                user_telegram = order['users'].get('telegram_id')
                if user_telegram:
                    try:
                        # Send text confirmation
                        bot.send_message(
                            user_telegram,
                            f"✅ **ክፍያዎ ተረጋግጧል!**\n\nትዕዛዝ #{payment['order_id'][:8]} ተረጋግጧል። በቅርቡ አድራሻዎ ላይ እናደርሳለን።",
                            parse_mode="Markdown"
                        )
                        
                        # Generate and dispatch professional image receipt
                        receipt_path = generate_receipt_image(order)
                        if receipt_path and os.path.exists(receipt_path):
                            with open(receipt_path, 'rb') as receipt_img:
                                bot.send_photo(
                                    user_telegram, 
                                    receipt_img, 
                                    caption="🧾 የእርስዎ የክፍያ ደረሰኝ ሰነድ። ስለመረጡን እናመሰግናለን!"
                                )
                            os.remove(receipt_path) # Cleanup temporary file
                    except Exception as client_err:
                        logger.error(f"Failed to deliver notification/receipt to user {user_telegram}: {client_err}")
            
            bot.edit_message_text(
                f"✅ Payment {payment_id[:8]} verified successfully!",
                call.message.chat.id,
                call.message.message_id
            )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("reject_pay_"))
    def reject_payment(call):
        admin_user_id = call.from_user.id
        if admin_user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ ይህ እርምጃ ለእርስዎ አልተፈቀደም!", show_alert=True)
            return
        
        payment_id = call.data.replace("reject_pay_", "")
        bot.answer_callback_query(call.id, "❌ Payment Rejected")
        
        # DB Updates: Mark payment and order as rejected/cancelled
        payment = db.get_payment(payment_id)
        if payment:
            db.update_payment_status(payment_id, 'rejected')
            db.update_order_status(payment['order_id'], 'cancelled')
            
            # Inform customer about rejection reason
            order = db.get_order(payment['order_id'])
            if order and order.get('users'):
                user_telegram = order['users'].get('telegram_id')
                if user_telegram:
                    try:
                        bot.send_message(
                            user_telegram,
                            f"❌ **የክፍያ ማረጋገጫ አልተሳካም**\n\nለማዘዣ #{order['id'][:8]} ያስገቡት የማጣቀሻ ቁጥር (Reference Code) በአስተዳዳሪ ውድቅ ተደርጓል። እባክዎ ክፍያውን ደግመው ይሞክሩ ወይም በአግባቡ መፈጸሙን ያረጋግጡ።"
                        )
                    except Exception as client_err:
                        logger.error(f"Failed to notify user {user_telegram} of rejection: {client_err}")

        bot.edit_message_text(
            f"❌ Payment {payment_id[:8]} rejected. Customer notified.",
            call.message.chat.id,
            call.message.message_id
        )