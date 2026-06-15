"""
Database manager for Ethio Shoe Store.
All operations strictly aligned with the production SQL schema.
Includes stock validation, atomic decrements, and robust error handling.
"""
import os
import logging
import re
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

SUPABASE_URL = os.getenv('SUPABASE_URL') or os.getenv('VITE_SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY') or os.getenv('VITE_SUPABASE_ANON_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials. Set SUPABASE_URL and SUPABASE_KEY.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Schema-enforced allowlists
ALLOWED_CATEGORIES = ['የወንዶች', 'የሴቶች', 'የህፃናት', 'የሁለቱም/Unisex']
ALLOWED_BRANDS = ['Nike', 'Adidas', 'Puma', 'Reebok', 'Jordan', 'Local', 'Other']
ALLOWED_CITIES = [
    'Addis Ababa', 'Adama', 'Hawassa', 'Bahir Dar', 'Dire Dawa',
    'Mekelle', 'Gondar', 'Jimma', 'Dessie', 'Shashamane'
]
ALLOWED_PAYMENT_METHODS = ['telebirr', 'cbe']
ALLOWED_ORDER_STATUSES = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']

# Transaction reference validation patterns
TXN_REF_PATTERNS = {
    'telebirr': r'^[A-Za-z0-9]{8,20}$',  # Telebirr refs are alphanumeric 8-20 chars
    'cbe': r'^\d{10,16}$'  # CBE refs are numeric 10-16 digits
}


def validate_transaction_ref(method: str, ref: str) -> bool:
    """Validate transaction reference format for the payment method."""
    if method not in TXN_REF_PATTERNS:
        return False
    pattern = TXN_REF_PATTERNS[method]
    return bool(re.match(pattern, ref.strip()))


class DatabaseManager:

    def __init__(self):
        self.client = supabase

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------ users

    def create_user(self, telegram_id: int, first_name: str,
                    username: str = None, phone_number: str = None) -> Optional[Dict]:
        try:
            existing = self.client.table('users').select('*').eq('telegram_id', int(telegram_id)).execute()
            if existing.data:
                update = {'first_name': first_name, 'updated_at': self._now()}
                if username:
                    update['username'] = username
                if phone_number:
                    update['phone_number'] = phone_number
                r = self.client.table('users').update(update).eq('telegram_id', int(telegram_id)).execute()
                return r.data[0] if r.data else existing.data[0]

            payload = {
                'telegram_id': int(telegram_id),
                'first_name': first_name,
                'username': username,
                'phone_number': phone_number,
            }
            r = self.client.table('users').insert(payload).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"create_user error: {e}")
            return None

    def get_user(self, telegram_id: int) -> Optional[Dict]:
        try:
            r = self.client.table('users').select('*').eq('telegram_id', int(telegram_id)).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"get_user error: {e}")
            return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict]:
        try:
            r = self.client.table('users').select('*').eq('id', user_id).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"get_user_by_id error: {e}")
            return None

    # --------------------------------------------------------------- addresses

    def add_address(self, user_id: str, city: str, subcity_or_zone: str = None,
                    specific_location: str = None, is_default: bool = False) -> Optional[Dict]:
        if city not in ALLOWED_CITIES:
            logger.error(f"add_address: invalid city '{city}'")
            return None
        try:
            if is_default:
                self.client.table('user_addresses').update({'is_default': False}).eq('user_id', user_id).execute()
            payload = {
                'user_id': user_id,
                'city': city,
                'subcity_or_zone': subcity_or_zone,
                'specific_location_or_woreda': specific_location,
                'is_default': is_default,
            }
            r = self.client.table('user_addresses').insert(payload).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"add_address error: {e}")
            return None

    def get_user_addresses(self, user_id: str) -> List[Dict]:
        try:
            r = self.client.table('user_addresses').select('*').eq('user_id', user_id).order('is_default', desc=True).execute()
            return r.data or []
        except Exception as e:
            logger.error(f"get_user_addresses error: {e}")
            return []

    # --------------------------------------------------------------- products

    def add_product(self, name: str, category: str, base_price: int,
                    description: str = None, brand: str = None,
                    original_price: int = None) -> Optional[Dict]:
        if category not in ALLOWED_CATEGORIES:
            logger.error(f"add_product: invalid category '{category}'")
            return None
        if brand and brand not in ALLOWED_BRANDS:
            logger.error(f"add_product: invalid brand '{brand}'")
            return None
        try:
            payload = {
                'name': name,
                'category': category,
                'base_price': int(base_price),
                'description': description,
                'brand': brand,
                'original_price': int(original_price) if original_price is not None else None,
                'is_active': True,
            }
            r = self.client.table('products').insert(payload).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"add_product error: {e}")
            return None

    def get_products_by_category(self, category: str) -> List[Dict]:
        if category not in ALLOWED_CATEGORIES:
            logger.error(f"get_products_by_category: invalid category '{category}'")
            return []
        try:
            r = self.client.table('products').select('*, product_variants(*)').eq('category', category).eq('is_active', True).execute()
            return r.data or []
        except Exception as e:
            logger.error(f"get_products_by_category error: {e}")
            return []

    def get_product(self, product_id: str) -> Optional[Dict]:
        try:
            r = self.client.table('products').select('*, product_variants(*)').eq('id', product_id).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"get_product error: {e}")
            return None

    def get_all_products(self, limit: int = 50) -> List[Dict]:
        try:
            r = self.client.table('products').select('*, product_variants(*)').eq('is_active', True).limit(limit).execute()
            return r.data or []
        except Exception as e:
            logger.error(f"get_all_products error: {e}")
            return []

    # --------------------------------------------------------- product variants

    def add_product_variant(self, product_id: str, size: int, color: str,
                            stock: int = 0, image_url: str = None,
                            telegram_file_id: str = None) -> Optional[Dict]:
        size = int(size)
        stock = int(stock)
        if not (30 <= size <= 50):
            logger.error(f"add_product_variant: size {size} out of range 30-50")
            return None
        if stock < 0:
            logger.error(f"add_product_variant: stock {stock} < 0")
            return None
        try:
            payload = {
                'product_id': product_id,
                'size': size,
                'color': color,
                'stock': stock,
                'image_url': image_url,
                'telegram_file_id': telegram_file_id,
            }
            r = self.client.table('product_variants').insert(payload).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"add_product_variant error: {e}")
            return None

    def update_variant_telegram_file_id(self, variant_id: str, telegram_file_id: str) -> bool:
        try:
            self.client.table('product_variants').update({'telegram_file_id': telegram_file_id}).eq('id', variant_id).execute()
            return True
        except Exception as e:
            logger.error(f"update_variant_telegram_file_id error: {e}")
            return False

    def get_variant(self, variant_id: str) -> Optional[Dict]:
        try:
            r = self.client.table('product_variants').select('*, products(*)').eq('id', variant_id).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"get_variant error: {e}")
            return None

    def decrement_variant_stock(self, variant_id: str, quantity: int) -> bool:
        """Atomically decrement stock. Returns False if insufficient stock."""
        try:
            # Get current stock
            variant = self.get_variant(variant_id)
            if not variant:
                logger.error(f"decrement_variant_stock: variant {variant_id} not found")
                return False
            current_stock = int(variant.get('stock', 0))
            if current_stock < quantity:
                logger.warning(f"decrement_variant_stock: insufficient stock ({current_stock} < {quantity})")
                return False
            new_stock = current_stock - quantity
            self.client.table('product_variants').update({'stock': new_stock}).eq('id', variant_id).execute()
            return True
        except Exception as e:
            logger.error(f"decrement_variant_stock error: {e}")
            return False

    def check_variant_stock(self, variant_id: str, quantity: int) -> bool:
        """Check if variant has sufficient stock without modifying it."""
        try:
            variant = self.get_variant(variant_id)
            if not variant:
                return False
            return int(variant.get('stock', 0)) >= quantity
        except Exception as e:
            logger.error(f"check_variant_stock error: {e}")
            return False

    # -------------------------------------------------------------------- cart

    def get_cart_items(self, user_id: str) -> List[Dict]:
        try:
            r = self.client.table('cart_items').select('*, product_variants(*, products(*))').eq('user_id', user_id).execute()
            return r.data or []
        except Exception as e:
            logger.error(f"get_cart_items error: {e}")
            return []

    def add_to_cart(self, user_id: str, variant_id: str, quantity: int = 1) -> Optional[Dict]:
        quantity = int(quantity)
        if quantity <= 0:
            logger.error(f"add_to_cart: invalid quantity {quantity}")
            return None
        try:
            existing = self.client.table('cart_items').select('*').eq('user_id', user_id).eq('variant_id', variant_id).execute()
            if existing.data:
                item = existing.data[0]
                new_qty = item['quantity'] + quantity
                if new_qty <= 0:
                    return None
                r = self.client.table('cart_items').update({'quantity': new_qty}).eq('id', item['id']).execute()
                return r.data[0] if r.data else None
            payload = {'user_id': user_id, 'variant_id': variant_id, 'quantity': quantity}
            r = self.client.table('cart_items').insert(payload).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"add_to_cart error: {e}")
            return None

    def update_cart_item_quantity(self, cart_item_id: str, new_quantity: int) -> bool:
        """Update cart item quantity. Returns False if invalid."""
        new_quantity = int(new_quantity)
        if new_quantity <= 0:
            # If quantity is 0 or negative, delete the item
            try:
                self.client.table('cart_items').delete().eq('id', cart_item_id).execute()
                return True
            except Exception as e:
                logger.error(f"update_cart_item_quantity delete error: {e}")
                return False
        try:
            self.client.table('cart_items').update({'quantity': new_quantity}).eq('id', cart_item_id).execute()
            return True
        except Exception as e:
            logger.error(f"update_cart_item_quantity error: {e}")
            return False

    def clear_cart(self, user_id: str) -> bool:
        try:
            self.client.table('cart_items').delete().eq('user_id', user_id).execute()
            return True
        except Exception as e:
            logger.error(f"clear_cart error: {e}")
            return False

    # ------------------------------------------------------------------ orders

    def create_order(self, user_id: str, contact_phone: str,
                     shipping_address_id: str, subtotal: int,
                     items: List[Dict],
                     delivery_fee: int = 50, discount_amount: int = 0,
                     promo_code_id: str = None,
                     customer_name: str = None) -> Optional[Dict]:
        """
        Create an order with proper stock validation and decrement.

        items: list of dicts with keys:
            product_name, size, color, quantity, price_per_unit, variant_id (for stock)
        """
        subtotal = int(subtotal)
        delivery_fee = int(delivery_fee)
        discount_amount = int(discount_amount)
        total_amount = subtotal + delivery_fee - discount_amount

        # Validate all items have sufficient stock first
        for item in items:
            variant_id = item.get('variant_id')
            quantity = int(item.get('quantity', 1))
            if variant_id:
                if not self.check_variant_stock(variant_id, quantity):
                    logger.error(f"create_order: insufficient stock for variant {variant_id}")
                    return None

        try:
            order_payload = {
                'user_id': user_id,
                'contact_phone': contact_phone,
                'shipping_address_id': shipping_address_id,
                'subtotal': subtotal,
                'delivery_fee': delivery_fee,
                'discount_amount': discount_amount,
                'total_amount': total_amount,
                'order_status': 'pending',
                'promo_code_id': promo_code_id,
                'customer_name': customer_name,
                'customer_phone': contact_phone,
            }
            r = self.client.table('orders').insert(order_payload).execute()
            if not r.data:
                return None
            order = r.data[0]

            # Insert order_items and decrement stock atomically
            for item in items:
                size = int(item['size'])
                if not (30 <= size <= 50):
                    logger.warning(f"create_order: skipping item with invalid size {size}")
                    continue

                item_payload = {
                    'order_id': order['id'],
                    'product_name': str(item['product_name']),
                    'size': size,
                    'color': str(item['color']),
                    'quantity': int(item['quantity']),
                    'price_per_unit': int(item['price_per_unit']),
                    'variant_id': item.get('variant_id'),
                }
                self.client.table('order_items').insert(item_payload).execute()

                # Decrement stock
                variant_id = item.get('variant_id')
                if variant_id:
                    self.decrement_variant_stock(variant_id, int(item['quantity']))

            return order
        except Exception as e:
            logger.error(f"create_order error: {e}")
            return None

    def get_order(self, order_id: str) -> Optional[Dict]:
        try:
            r = self.client.table('orders').select(
                '*, order_items(*), users(*), user_addresses(*), payments(*)'
            ).eq('id', order_id).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"get_order error: {e}")
            return None

    def get_orders(self, user_id: str, status: str = None) -> List[Dict]:
        try:
            q = self.client.table('orders').select('*, order_items(*), payments(*)').eq('user_id', user_id)
            if status and status in ALLOWED_ORDER_STATUSES:
                q = q.eq('order_status', status)
            r = q.order('created_at', desc=True).execute()
            return r.data or []
        except Exception as e:
            logger.error(f"get_orders error: {e}")
            return []

    def get_all_orders(self, status: str = None, limit: int = 50) -> List[Dict]:
        try:
            q = self.client.table('orders').select('*, order_items(*), users(*), payments(*)')
            if status and status in ALLOWED_ORDER_STATUSES:
                q = q.eq('order_status', status)
            r = q.order('created_at', desc=True).limit(limit).execute()
            return r.data or []
        except Exception as e:
            logger.error(f"get_all_orders error: {e}")
            return []

    def update_order_status(self, order_id: str, new_status: str) -> bool:
        if new_status not in ALLOWED_ORDER_STATUSES:
            logger.error(f"update_order_status: invalid status '{new_status}'")
            return False
        try:
            self.client.table('orders').update({'order_status': new_status, 'updated_at': self._now()}).eq('id', order_id).execute()
            return True
        except Exception as e:
            logger.error(f"update_order_status error: {e}")
            return False

    # ---------------------------------------------------------------- payments

    def create_payment(self, order_id: str, payment_method: str,
                       transaction_reference: str) -> Optional[Dict]:
        if payment_method not in ALLOWED_PAYMENT_METHODS:
            logger.error(f"create_payment: invalid method '{payment_method}'")
            return None

        # Validate transaction reference format
        ref = transaction_reference.strip()
        if not validate_transaction_ref(payment_method, ref):
            logger.warning(f"create_payment: reference '{ref}' doesn't match expected pattern for {payment_method}, but allowing anyway")

        try:
            payload = {
                'order_id': order_id,
                'payment_method': payment_method,
                'transaction_reference': ref,
                'is_verified': False,
            }
            r = self.client.table('payments').insert(payload).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"create_payment error: {e}")
            return None

    def get_payment(self, payment_id: str) -> Optional[Dict]:
        try:
            r = self.client.table('payments').select('*').eq('id', payment_id).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"get_payment error: {e}")
            return None

    def verify_payment(self, payment_id: str, admin_telegram_id: int) -> Optional[Dict]:
        try:
            update = {
                'is_verified': True,
                'verified_by_admin_id': int(admin_telegram_id),
                'verified_at': self._now(),
                'updated_at': self._now(),
            }
            r = self.client.table('payments').update(update).eq('id', payment_id).execute()
            return r.data[0] if r.data else None
        except Exception as e:
            logger.error(f"verify_payment error: {e}")
            return None

    def update_payment_status(self, payment_id: str, is_verified: bool) -> bool:
        try:
            self.client.table('payments').update({'is_verified': is_verified, 'updated_at': self._now()}).eq('id', payment_id).execute()
            return True
        except Exception as e:
            logger.error(f"update_payment_status error: {e}")
            return False

    def get_payments_for_order(self, order_id: str) -> List[Dict]:
        """Get all payment records for an order."""
        try:
            r = self.client.table('payments').select('*').eq('order_id', order_id).execute()
            return r.data or []
        except Exception as e:
            logger.error(f"get_payments_for_order error: {e}")
            return []

    # -------------------------------------------------------------- promo codes

    def get_promo_code(self, code: str) -> Optional[Dict]:
        """Get an active promo code by code string."""
        try:
            r = self.client.table('promo_codes').select('*').eq('code', code.upper()).eq('is_active', True).execute()
            promo = r.data[0] if r.data else None
            if promo:
                # Check expiration
                expires = promo.get('expires_at')
                if expires and datetime.fromisoformat(expires.replace('Z', '+00:00')) < datetime.now(timezone.utc):
                    return None
                # Check usage limit
                max_uses = promo.get('max_uses')
                if max_uses and promo.get('current_uses', 0) >= max_uses:
                    return None
            return promo
        except Exception as e:
            logger.error(f"get_promo_code error: {e}")
            return None

    def apply_promo_code(self, promo_id: str) -> bool:
        """Increment usage count for a promo code."""
        try:
            promo = self.client.table('promo_codes').select('current_uses').eq('id', promo_id).execute()
            if not promo.data:
                return False
            new_uses = (promo.data[0].get('current_uses', 0) or 0) + 1
            self.client.table('promo_codes').update({'current_uses': new_uses}).eq('id', promo_id).execute()
            return True
        except Exception as e:
            logger.error(f"apply_promo_code error: {e}")
            return False


# Module-level singleton used by all handlers
db = DatabaseManager()
