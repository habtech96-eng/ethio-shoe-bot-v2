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
        
        # Get user
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
        
        # Set order state
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
        
        # Send contact request button
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
        
        # Get user addresses
        addresses = db.get_user_addresses(user_id)
        
        if addresses:
            # Show address selection
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
        
        # Proceed to payment method selection
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
        
        # Parse address (simplified)
        parts = address_text.split(',')
        city = parts[0].strip() if len(parts) > 0 else "Addis Ababa"
        subcity = parts[1].strip() if len(parts) > 1 else ""
        specific = parts[2].strip() if len(parts) > 2 else ""
        
        with bot.retrieve_data(chat_id) as data:
            # Add address to database
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
            product_name = data['product_name']
            
            # Calculate totals (simplified - single item order)
            subtotal = price_per_unit
            delivery_fee = 50  # Fixed delivery fee
            total = subtotal + delivery_fee
            
            data['subtotal'] = subtotal
            data['delivery_fee'] = delivery_fee
            data['total'] = total
        
        # Show payment details
        payment_info = (
            f"💳 **የክፍያ መረጃ**\n\n"
            f"👟 **ምርት:** {data['product_name']}\n"
            f"📐 **Size:** {data['size']}\n"
            f"🎨 **Color:** {data['color']}\n"
            f"💵 **ዋጋ:** {subtotal} ETB (ብር)\n"
            f"🚚 **የመጓጓዣ ክፍያ:** {delivery_fee} ETB (ብር)\n"
            f"💰 **ጠቅላላ:** {total} ETB (ብር)\n\n"
        )
        
        if payment_method == "telebirr":
            payment_info += (
                f"📱 **Telebirr Payment**\n"
                f"Phone: 0938649925\n\n"
                f"ክፍያውን ከፈጸሙ በኋላ የማረጋገጫ ኮዱን (Reference) ያስገቡ፦"
            )
        else:
            payment_info += (
                f"🏦 **CBE Bank Payment**\n"
                f"Account: 1000274286637\n\n"
                f"ክፍያውን ከፈጸሙ በኋላ የማረጋገጫ ኮዱን (Reference) ያስገባ፦"
            )
        
        bot.send_message(chat_id, payment_info, parse_mode="Markdown")
        bot.set_state(chat_id, CustomerOrderStates.waiting_for_transaction_ref)

    @bot.message_handler(state=CustomerOrderStates.waiting_for_transaction_ref)
    def process_transaction_ref(message):
        chat_id = message.chat.id
        transaction_ref = message.text.strip()
        
        with bot.retrieve_data(chat_id) as data:
            # Create order in database
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
            
            # Create payment record
            payment = db.create_payment(
                order_id=order['id'],
                payment_method=data['payment_method'],
                transaction_reference=transaction_ref
            )
            
            if payment:
                # Notify customer
                success_msg = (
                    f"✅ **ትዕዛዝዎ በተሳካ ሁኔታ ተመዝግቧል!**\n\n"
                    f"🆔 **Order ID:** #{order['id'][:8]}\n"
                    f"👟 **ምርት:** {data['product_name']}\n"
                    f"💰 **ጠቅላላ:** {data['total']} ETB (ብር)\n\n"
                    f"⏳ **መጨረሻ ማረጋገጫ፦** ክፍያዎ ተረግጎ ምርትዎ ወዲያውኑ ይመጣል።"
                )
                bot.send_message(chat_id, success_msg, parse_mode="Markdown")
                
                # Notify admin
                admin_alert = (
                    f"🆕 **አዲስ ትዕዛዝ!**\n\n"
                    f"🆔 Order ID: #{order['id'][:8]}\n"
                    f"👤 Customer: {data['customer_name']}\n"
                    f"📞 Phone: {data['phone']}\n"
                    f"👟 Product: {data['product_name']} (Size {data['size']}, {data['color']})\n"
                    f"💳 Payment: {data['payment_method'].upper()}\n"
                    f"📝 Ref: {transaction_ref}\n"
                    f"💰 Total: {data['total']} ETB (ብር)"
                )
                
                markup = InlineKeyboardMarkup(row_width=1)
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
        chat_id = call.message.chat.id
        if chat_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ ይህ እርምጃ ለእርስዎ አልተፈቀደም!", show_alert=True)
            return
        
        payment_id = call.data.replace("verify_pay_", "")
        bot.answer_callback_query(call.id, "✅ Payment Verified!")
        
        # Verify payment in database
        payment = db.verify_payment(payment_id, chat_id)
        
        if payment:
            # Update order status to confirmed
            db.update_order_status(payment['order_id'], 'confirmed')
            
            # Notify customer
            # (Need to get user from order)
            order = db.get_order(payment['order_id'])
            if order and order.get('users'):
                user_telegram = order['users'].get('telegram_id')
                if user_telegram:
                    try:
                        bot.send_message(
                            user_telegram,
                            f"✅ **ክፍያዎ ተረግጓል!**\n\nOrder #{payment['order_id'][:8]} confirmed and will be shipped soon.",
                            parse_mode="Markdown"
                        )
                    except:
                        pass
            
            bot.edit_message_text(
                f"✅ Payment {payment_id[:8]} verified!",
                call.message.chat.id,
                call.message.message_id
            )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("reject_pay_"))
    def reject_payment(call):
        chat_id = call.message.chat.id
        if chat_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ ይህ እርምጃ ለእርስዎ አልተፈቀደም!", show_alert=True)
            return
        
        payment_id = call.data.replace("reject_pay_", "")
        bot.answer_callback_query(call.id, "❌ Payment Rejected")
        
        # Get payment to find order
        payment = db.get_payment_by_order(payment_id.split('_')[0])  # Simplified
        
        bot.edit_message_text(
            f"❌ Payment {payment_id[:8]} rejected.",
            call.message.chat.id,
            call.message.message_id
        )
