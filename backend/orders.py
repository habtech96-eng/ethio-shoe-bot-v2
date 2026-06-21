"""
Order management handlers for Ethio Shoe Store.
Handles checkout from cart, address collection, payment method selection,
transaction reference submission, and admin payment verification.
State management uses (from_user.id, chat_id) correctly for pyTelegramBotAPI 4.x.
"""
import sys
import os
import logging
import telebot
from telebot.handler_backends import State, StatesGroup
from telebot.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)

from . import database as db
from .receipt import generate_receipt_image

try:
    from config import ADMIN_IDS
except ImportError:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from config import ADMIN_IDS

logger = logging.getLogger(__name__)

ALLOWED_CITIES = [
    'Addis Ababa', 'Adama', 'Hawassa', 'Bahir Dar', 'Dire Dawa',
    'Mekelle', 'Gondar', 'Jimma', 'Dessie', 'Shashamane'
]

TELEBIRR_PHONE = os.getenv('PAYMENT_TELEBIRR_PHONE', '0938649925')
CBE_ACCOUNT    = os.getenv('PAYMENT_CBE_ACCOUNT',    '1000274286637')


class CustomerOrderStates(StatesGroup):
    waiting_for_phone           = State()
    waiting_for_address_choice  = State()
    waiting_for_city            = State()
    waiting_for_subcity         = State()
    waiting_for_payment_method  = State()
    waiting_for_transaction_ref = State()


def register_order_handlers(bot):

    # ----------------------------------------------------------------
    # Checkout — triggered from cart "Checkout" inline button
    # ----------------------------------------------------------------

    @bot.callback_query_handler(func=lambda call: call.data == "checkout")
    def start_checkout(call):
        chat_id     = call.message.chat.id
        telegram_id = call.from_user.id
        bot.answer_callback_query(call.id)

        user = db.db.get_user(telegram_id)
        if not user:
            user = db.db.create_user(telegram_id,
                                     call.from_user.first_name,
                                     call.from_user.username)
            if not user:
                bot.send_message(chat_id, "❌ ስህተት። /start ን ጫኑ።")
                return

        cart_items = db.db.get_cart_items(user['id'])
        if not cart_items:
            bot.send_message(chat_id, "🛒 ጋሪዎ ባዶ ነው።")
            return

        subtotal        = 0
        order_items_data = []
        for item in cart_items:
            variant = item.get('product_variants') or {}
            if isinstance(variant, list):
                variant = variant[0] if variant else {}
            product = variant.get('products') or {}
            if isinstance(product, list):
                product = product[0] if product else {}

            qty   = int(item.get('quantity', 1))
            price = int(product.get('base_price', 0))
            subtotal += price * qty
            order_items_data.append({
                'product_name':  product.get('name', 'ጫማ'),
                'size':          int(variant.get('size', 38)),
                'color':         variant.get('color', 'N/A'),
                'quantity':      qty,
                'price_per_unit': price,
                'variant_id':    variant.get('id'),  # For stock decrement
            })

        delivery_fee = 50
        total        = subtotal + delivery_fee

        bot.set_state(telegram_id, CustomerOrderStates.waiting_for_phone, chat_id)
        with bot.retrieve_data(telegram_id, chat_id) as data:
            data['user_id']       = user['id']
            data['order_items']   = order_items_data
            data['subtotal']      = subtotal
            data['delivery_fee']  = delivery_fee
            data['total']         = total
            data['customer_name'] = (
                f"{call.from_user.first_name or ''} {call.from_user.last_name or ''}".strip()
            )

        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
        markup.add(KeyboardButton("📱 ስልኬን ላክ", request_contact=True))
        bot.send_message(
            chat_id,
            f"✅ <b>ጋሪ ማጠቃለያ</b>\n\n"
            f"💵 ድምር: {subtotal} ETB\n"
            f"🚚 ማድረሻ: {delivery_fee} ETB\n"
            f"💰 <b>ጠቅላላ: {total} ETB</b>\n\n"
            f"📱 ስልክ ቁጥርዎን ያጋሩ ወይም በጽሑፍ ያስገቡ፦",
            parse_mode="HTML",
            reply_markup=markup
        )

    # ---------------------------------------------------------------- phone

    @bot.message_handler(state=CustomerOrderStates.waiting_for_phone,
                         content_types=['contact', 'text'])
    def process_phone(message):
        chat_id     = message.chat.id
        telegram_id = message.from_user.id

        if message.content_type == 'contact' and message.contact:
            phone = message.contact.phone_number
            logger.info(f"Contact shared for user {telegram_id}: {phone}")
        else:
            phone = message.text.strip() if message.text else ''
            if not phone or len(phone) < 7:
                bot.send_message(chat_id, "⚠️ ትክክለኛ ስልክ ቁጥር ያስገባ፦")
                return

        with bot.retrieve_data(telegram_id, chat_id) as data:
            data['phone'] = phone
            user_id       = data['user_id']

        # CRITICAL: Save phone to user record in database immediately
        try:
            db.db.update_user_phone(user_id, phone)
            logger.info(f"Updated phone for user {user_id}")
        except Exception as e:
            logger.error(f"Failed to update user phone: {e}")

        # CRITICAL: Clear the contact keyboard BEFORE showing address options
        bot.send_message(chat_id, "✅ ስልክ ቁጥር ተቀምጧል!", reply_markup=ReplyKeyboardRemove())

        addresses = db.db.get_user_addresses(user_id)
        if addresses:
            markup = InlineKeyboardMarkup(row_width=1)
            for addr in addresses:
                loc = f"{addr['city']} - {addr.get('subcity_or_zone', '')}".strip(' -')
                markup.add(InlineKeyboardButton(f"📍 {loc}",
                                                callback_data=f"addr_{addr['id']}"))
            markup.add(InlineKeyboardButton("➕ አዲስ አድራሻ", callback_data="addr_new"))
            bot.set_state(telegram_id, CustomerOrderStates.waiting_for_address_choice, chat_id)
            bot.send_message(chat_id, "📍 አድራሻ ይምረጡ ወይም አዲስ ያስገቡ፦",
                             reply_markup=markup)
        else:
            _ask_city(bot, chat_id, telegram_id)

    # ---------------------------------------------------------------- address choice

    @bot.callback_query_handler(func=lambda call: call.data.startswith("addr_"),
                                 state=CustomerOrderStates.waiting_for_address_choice)
    def handle_address_choice(call):
        chat_id     = call.message.chat.id
        telegram_id = call.from_user.id
        bot.answer_callback_query(call.id)

        if call.data == "addr_new":
            _ask_city(bot, chat_id, telegram_id)
        else:
            address_id = call.data.replace("addr_", "", 1)
            with bot.retrieve_data(telegram_id, chat_id) as data:
                data['address_id'] = address_id
            _ask_payment_method(bot, chat_id, telegram_id)

    # ---------------------------------------------------------------- city

    def _ask_city(bot, chat_id, telegram_id):
        markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
        markup.add(*[KeyboardButton(c) for c in ALLOWED_CITIES])
        bot.set_state(telegram_id, CustomerOrderStates.waiting_for_city, chat_id)
        bot.send_message(chat_id, "🏙️ ከተማ ይምረጡ፦", reply_markup=markup)

    @bot.message_handler(state=CustomerOrderStates.waiting_for_city,
                         content_types=['text'])
    def process_city(message):
        chat_id     = message.chat.id
        telegram_id = message.from_user.id
        city        = message.text.strip() if message.text else ""

        if city not in ALLOWED_CITIES:
            markup = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True, row_width=2)
            markup.add(*[KeyboardButton(c) for c in ALLOWED_CITIES])
            bot.send_message(chat_id, "⚠️ ከዝርዝሩ ውስጥ ከተማ ይምረጡ፦", reply_markup=markup)
            return

        with bot.retrieve_data(telegram_id, chat_id) as data:
            data['city'] = city

        bot.set_state(telegram_id, CustomerOrderStates.waiting_for_subcity, chat_id)
        bot.send_message(chat_id, "📍 ሰፈር / ወረዳ ያስገቡ (ምሳሌ: Bole, Woreda 03)፦",
                         reply_markup=ReplyKeyboardRemove())

    @bot.message_handler(state=CustomerOrderStates.waiting_for_subcity,
                         content_types=['text'])
    def process_subcity(message):
        chat_id     = message.chat.id
        telegram_id = message.from_user.id
        subcity     = message.text.strip() if message.text else ""

        with bot.retrieve_data(telegram_id, chat_id) as data:
            user_id = data['user_id']
            city    = data['city']

        address = db.db.add_address(
            user_id=user_id,
            city=city,
            subcity_or_zone=subcity,
            specific_location=None,
            is_default=False,
        )
        if not address:
            bot.send_message(chat_id, "❌ አድራሻ ማስቀመጥ አልተሳካም። ደግሞ ይሞክሩ።")
            bot.delete_state(telegram_id, chat_id)
            return

        with bot.retrieve_data(telegram_id, chat_id) as data:
            data['address_id'] = address['id']

        _ask_payment_method(bot, chat_id, telegram_id)

    # ---------------------------------------------------------------- payment method

    def _ask_payment_method(bot, chat_id, telegram_id):
        markup = InlineKeyboardMarkup(row_width=1)
        markup.add(
            InlineKeyboardButton("📱 ቴሌቢር (Telebirr)", callback_data="pay_telebirr"),
            InlineKeyboardButton("🏦 ሲቢኢ (CBE Bank)", callback_data="pay_cbe"),
        )
        bot.set_state(telegram_id, CustomerOrderStates.waiting_for_payment_method, chat_id)
        bot.send_message(chat_id, "💳 የክፍያ ዘዴ ይምረጡ፦", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("pay_"),
                                 state=CustomerOrderStates.waiting_for_payment_method)
    def select_payment_method(call):
        chat_id     = call.message.chat.id
        telegram_id = call.from_user.id
        method      = call.data.replace("pay_", "", 1)

        if method not in ('telebirr', 'cbe'):
            bot.answer_callback_query(call.id, "⚠️ ያልታወቀ ዘዴ።", show_alert=True)
            return
        bot.answer_callback_query(call.id)

        with bot.retrieve_data(telegram_id, chat_id) as data:
            data['payment_method'] = method
            subtotal     = data['subtotal']
            delivery_fee = data['delivery_fee']
            total        = data['total']
            items        = data.get('order_items', [])

        items_text = "".join(
            f"  • {it['product_name']} (Size {it['size']}, {it['color']}) "
            f"x{it['quantity']} — {it['price_per_unit']} ETB\n"
            for it in items
        )

        if method == "telebirr":
            instructions = (
                f"📱 <b>Telebirr</b>\n"
                f"ስልክ: <code>{TELEBIRR_PHONE}</code>\n\n"
                f"ክፍያ ከፈጸሙ በኋላ <b>Transaction Reference</b> ያስገቡ፦"
            )
        else:
            instructions = (
                f"🏦 <b>CBE Bank Transfer</b>\n"
                f"Account: <code>{CBE_ACCOUNT}</code>\n\n"
                f"ክፍያ ከፈጸሙ በኋላ <b>Transaction Reference</b> ያስገቡ፦"
            )

        bot.send_message(chat_id,
            f"🧾 <b>የትዕዛዝ ማጠቃለያ</b>\n\n"
            f"{items_text}\n"
            f"💵 ድምር: {subtotal} ETB\n"
            f"🚚 ማድረሻ: {delivery_fee} ETB\n"
            f"💰 <b>ጠቅላላ: {total} ETB</b>\n\n"
            f"{instructions}",
            parse_mode="HTML")
        bot.set_state(telegram_id, CustomerOrderStates.waiting_for_transaction_ref, chat_id)

    # ---------------------------------------------------------------- transaction reference

    @bot.message_handler(state=CustomerOrderStates.waiting_for_transaction_ref,
                         content_types=['text'])
    def process_transaction_ref(message):
        chat_id     = message.chat.id
        telegram_id = message.from_user.id
        txn_ref     = message.text.strip() if message.text else ""

        # Basic validation - minimum length and format
        if len(txn_ref) < 4:
            bot.send_message(chat_id, "⚠️ ትክክለኛ Reference ቁጥር ያስገቡ (ቢያንስ 4 ፊደላት)፦")
            return

        # Clean reference - remove spaces/dashes
        txn_ref = txn_ref.replace(" ", "").replace("-", "")

        logger.info(f"Processing order for user {telegram_id}, reference: {txn_ref}")

        try:
            with bot.retrieve_data(telegram_id, chat_id) as data:
                user_id        = data['user_id']
                phone          = data['phone']
                address_id     = data.get('address_id')
                subtotal       = data['subtotal']
                delivery_fee   = data['delivery_fee']
                total          = data['total']
                order_items    = data.get('order_items', [])
                payment_method = data['payment_method']
                customer_name  = data.get('customer_name', 'Customer')

                logger.info(f"Order data retrieved: user={user_id}, phone={phone}, address={address_id}, items={len(order_items)}")

        except Exception as e:
            logger.error(f"Failed to retrieve order data from state: {e}")
            bot.send_message(chat_id, "❌ የትዕዛዝ ዳታ ማግኘት አልተሳካም። /start ን ጫኑ።")
            bot.delete_state(telegram_id, chat_id)
            return

        if not address_id:
            bot.send_message(chat_id, "❌ አድራሻ አልተቀመጠም። ደግሞ ለመጀመር /start ን ጫኑ።")
            bot.delete_state(telegram_id, chat_id)
            return

        if not order_items:
            bot.send_message(chat_id, "❌ ጋሪ ባዶ ነው። እባክዎ ምርት ያክሉ።")
            bot.delete_state(telegram_id, chat_id)
            return

        try:
            order = db.db.create_order(
                user_id=user_id,
                contact_phone=phone,
                shipping_address_id=address_id,
                subtotal=subtotal,
                items=order_items,
                delivery_fee=delivery_fee,
                discount_amount=0,
                promo_code_id=None,
                customer_name=customer_name,
            )

            if not order:
                logger.error(f"create_order returned None for user {user_id}")
                bot.send_message(chat_id, "❌ ትዕዛዝ ማስቀመጥ አልተሳካም። ይህ የሚሆነው ክምችት በቂ ስለማይሆን ወይም የዳታቤዝ ችግር ሊሆን ይችላል። ደግሞ ይሞክሩ።")
                bot.delete_state(telegram_id, chat_id)
                return

            logger.info(f"Order created successfully: {order.get('id')}")

        except Exception as e:
            logger.error(f"create_order exception for user {user_id}: {e}", exc_info=True)
            bot.send_message(chat_id, "❌ ትዕዛዝ ማስቀመጥ አልተሳካም። ዳታቤዝ ችግር ተከስቷል። ቆይተው ይሞክሩ።")
            bot.delete_state(telegram_id, chat_id)
            return

        # Create payment record
        try:
            payment = db.db.create_payment(
                order_id=order['id'],
                payment_method=payment_method,
                transaction_reference=txn_ref,
            )

            if not payment:
                logger.error(f"create_payment returned None for order {order['id']}")
                bot.send_message(chat_id,
                    "⚠️ ትዕዛዙ ተቀምጧል ነገር ግን ክፍያ ማስቀመጥ አልተሳካም። Admin ያነጋግሩ።")
                bot.delete_state(telegram_id, chat_id)
                return

            logger.info(f"Payment created successfully: {payment.get('id')}")

        except Exception as e:
            logger.error(f"create_payment exception for order {order['id']}: {e}", exc_info=True)
            bot.send_message(chat_id,
                "⚠️ ትዕዛዙ ተቀምጧል ነገር ግን ክፍያ ማስቀመጥ አልተሳካም። እባክዎ ደግሞ ይሞክሩ።")
            bot.delete_state(telegram_id, chat_id)
            return

        # Clear cart only after successful order AND payment creation
        try:
            db.db.clear_cart(user_id)
            logger.info(f"Cart cleared for user {user_id}")
        except Exception as e:
            logger.error(f"clear_cart exception: {e}")

        # Success message to user
        bot.send_message(chat_id,
            f"✅ <b>ትዕዛዝዎ ተቀምጧል!</b>\n\n"
            f"🆔 Order: <code>#{order['id'][:8]}</code>\n"
            f"💰 ጠቅላላ: {total} ETB\n"
            f"💳 ክፍያ: {payment_method.upper()}\n\n"
            f"⏳ ክፍያዎ ከተረጋገጠ በኋላ ምርትዎ ይላካል።",
            parse_mode="HTML", reply_markup=ReplyKeyboardRemove())

        # Notify admins
        try:
            items_summary = ", ".join(
                f"{it['product_name']} ({it['size']}/{it['color']})" for it in order_items
            )
            admin_text = (
                f"🆕 <b>አዲስ ትዕዛዝ!</b>\n\n"
                f"🆔 <code>#{order['id'][:8]}</code>\n"
                f"👤 {customer_name} | 📞 {phone}\n"
                f"👟 {items_summary}\n"
                f"💳 {payment_method.upper()} Ref: <code>{txn_ref}</code>\n"
                f"💰 {total} ETB"
            )
            markup = InlineKeyboardMarkup(row_width=2)
            markup.add(
                InlineKeyboardButton("✅ Verify Payment",
                                     callback_data=f"verify_pay_{payment['id']}"),
                InlineKeyboardButton("❌ Reject",
                                     callback_data=f"reject_pay_{payment['id']}"),
            )
            for admin_id in ADMIN_IDS:
                try:
                    bot.send_message(admin_id, admin_text, parse_mode="HTML", reply_markup=markup)
                except Exception as e:
                    logger.error(f"Admin notification failed {admin_id}: {e}")
        except Exception as e:
            logger.error(f"Admin notification error: {e}")

        bot.delete_state(telegram_id, chat_id)

    # ---------------------------------------------------------------- admin: verify payment

    @bot.callback_query_handler(func=lambda call: call.data.startswith("verify_pay_"))
    def verify_payment(call):
        if call.from_user.id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ አልተፈቀደም!", show_alert=True)
            return
        payment_id = call.data.replace("verify_pay_", "", 1)
        bot.answer_callback_query(call.id, "✅ ክፍያ ተረጋግጧል!")

        payment = db.db.verify_payment(payment_id, call.from_user.id)
        if not payment:
            bot.edit_message_text("❌ ለማረጋገጥ አልተሳካም።",
                                  call.message.chat.id, call.message.message_id)
            return

        db.db.update_order_status(payment['order_id'], 'confirmed')
        order = db.db.get_order(payment['order_id'])

        if order:
            user_data = order.get('users') or {}
            tg_id = user_data.get('telegram_id') if isinstance(user_data, dict) else None
            if tg_id:
                try:
                    bot.send_message(tg_id,
                        f"✅ <b>ክፍያዎ ተረጋግጧል!</b>\n\n"
                        f"ትዕዛዝ <code>#{payment['order_id'][:8]}</code> ተረጋግጧል። "
                        f"በቅርቡ አድራሻዎ ላይ ያደርሳሉ።",
                        parse_mode="HTML")
                    receipt_path = generate_receipt_image(order)
                    if receipt_path and os.path.exists(receipt_path):
                        with open(receipt_path, 'rb') as f:
                            bot.send_photo(tg_id, f, caption="🧾 የክፍያ ደረሰኝ።")
                        os.remove(receipt_path)
                except Exception as e:
                    logger.error(f"Customer notify failed {tg_id}: {e}")

        bot.edit_message_text(
            f"✅ Payment <code>{payment_id[:8]}</code> verified.",
            call.message.chat.id, call.message.message_id, parse_mode="HTML")

    # ---------------------------------------------------------------- admin: reject payment

    @bot.callback_query_handler(func=lambda call: call.data.startswith("reject_pay_"))
    def reject_payment(call):
        if call.from_user.id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "❌ አልተፈቀደም!", show_alert=True)
            return
        payment_id = call.data.replace("reject_pay_", "", 1)
        bot.answer_callback_query(call.id, "❌ ውድቅ ተደርጓል።")

        payment = db.db.get_payment(payment_id)
        if payment:
            db.db.update_payment_status(payment_id, False)
            db.db.update_order_status(payment['order_id'], 'cancelled')
            order = db.db.get_order(payment['order_id'])
            if order:
                user_data = order.get('users') or {}
                tg_id = user_data.get('telegram_id') if isinstance(user_data, dict) else None
                if tg_id:
                    try:
                        bot.send_message(tg_id,
                            f"❌ <b>ክፍያ ውድቅ ተደርጓል።</b>\n\n"
                            f"ትዕዛዝ <code>#{payment['order_id'][:8]}</code> Reference ተቀባይነት አላገኘም። "
                            f"ደግሞ ይሞክሩ ወይም Admin ያነጋግሩ።",
                            parse_mode="HTML")
                    except Exception as e:
                        logger.error(f"Rejection notify failed {tg_id}: {e}")

        bot.edit_message_text(
            f"❌ Payment <code>{payment_id[:8]}</code> rejected.",
            call.message.chat.id, call.message.message_id, parse_mode="HTML")
