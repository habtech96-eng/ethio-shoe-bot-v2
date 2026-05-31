"""
Database connection and models for Ethiopian Shoe Store
PostgreSQL backend using Supabase
"""
import sys
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from supabase import create_client, Client
from dotenv import load_dotenv
import logging

# CRITICAL: Load environment variables properly
load_dotenv()

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase configuration - support both variable naming conventions
SUPABASE_URL = os.getenv('SUPABASE_URL') or os.getenv('VITE_SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY') or os.getenv('VITE_SUPABASE_ANON_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase configuration. Check environment variables")

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


class DatabaseManager:
    """Database manager for all shoe store operations"""

    def __init__(self):
        self.client = supabase

    def _get_current_time(self) -> str:
        """Helper to get current time in ISO format with UTC timezone"""
        return datetime.now(timezone.utc).isoformat()

    # ============================================================
    # USER MANAGEMENT
    # ============================================================

    def create_user(self, telegram_id: int, first_name: str, username: str = None, phone_number: str = None) -> Dict[str, Any]:
        """Create a new user or get existing user"""
        try:
            # Check if user exists
            existing = self.client.table('users').select('*').eq('telegram_id', telegram_id).execute()

            if existing.data:
                # Update user info if exists
                update_data = {'first_name': first_name, 'updated_at': self._get_current_time()}
                if username:
                    update_data['username'] = username
                if phone_number:
                    update_data['phone_number'] = phone_number

                result = self.client.table('users').update(update_data).eq('telegram_id', telegram_id).execute()
                return result.data[0] if result.data else existing.data[0]

            # Create new user
            user_data = {
                'telegram_id': telegram_id,
                'first_name': first_name,
                'username': username,
                'phone_number': phone_number
            }
            result = self.client.table('users').insert(user_data).execute()
            logger.info(f"Created new user: {telegram_id}")
            return result.data[0] if result.data else None

        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return None

    def get_user(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get user by telegram ID"""
        try:
            result = self.client.table('users').select('*').eq('telegram_id', telegram_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user: {e}")
            return None

    def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by UUID"""
        try:
            result = self.client.table('users').select('*').eq('id', user_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting user by ID: {e}")
            return None

    # ============================================================
    # ADDRESS MANAGEMENT
    # ============================================================

    def add_address(self, user_id: str, city: str, subcity_or_zone: str = None,
                    specific_location: str = None, is_default: bool = False) -> Optional[Dict[str, Any]]:
        """Add a new address for user"""
        try:
            # If setting as default, unset other defaults
            if is_default:
                self.client.table('user_addresses').update({'is_default': False}).eq('user_id', user_id).execute()

            address_data = {
                'user_id': user_id,
                'city': city,
                'subcity_or_zone': subcity_or_zone,
                'specific_location_or_woreda': specific_location,
                'is_default': is_default
            }
            result = self.client.table('user_addresses').insert(address_data).execute()
            logger.info(f"Added address for user: {user_id}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error adding address: {e}")
            return None

    def get_user_addresses(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all addresses for a user"""
        try:
            result = self.client.table('user_addresses').select('*').eq('user_id', user_id).order('is_default', desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting addresses: {e}")
            return []

    # ============================================================
    # PRODUCT MANAGEMENT
    # ============================================================

    def add_product(self, name: str, category: str, base_price: int, description: str = None,
                    brand: str = None, original_price: int = None) -> Optional[Dict[str, Any]]:
        """Add a new product"""
        try:
            product_data = {
                'name': name,
                'category': category,
                'base_price': base_price,
                'description': description,
                'brand': brand,
                'original_price': original_price,
                'is_active': True
            }
            result = self.client.table('products').insert(product_data).execute()
            logger.info(f"Added product: {name}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error adding product: {e}")
            return None

    def get_products_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get all active products by category with variants"""
        try:
            result = self.client.table('products').select(
                '*, product_variants(*)'
            ).eq('category', category).eq('is_active', True).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting products: {e}")
            return []

    def get_all_products(self) -> List[Dict[str, Any]]:
        """Get all active products with variants"""
        try:
            result = self.client.table('products').select(
                '*, product_variants(*)'
            ).eq('is_active', True).order('created_at', desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting all products: {e}")
            return []

    def get_product(self, product_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific product by ID with variants"""
        try:
            result = self.client.table('products').select(
                '*, product_variants(*)'
            ).eq('id', product_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting product: {e}")
            return None

    def update_product(self, product_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update a product"""
        try:
            update_data['updated_at'] = self._get_current_time()
            result = self.client.table('products').update(update_data).eq('id', product_id).execute()
            logger.info(f"Updated product: {product_id}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error updating product: {e}")
            return None

    def delete_product(self, product_id: str) -> bool:
        """Delete a product (soft delete)"""
        try:
            result = self.client.table('products').update({'is_active': False, 'updated_at': self._get_current_time()}).eq('id', product_id).execute()
            logger.info(f"Deleted product: {product_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting product: {e}")
            return False

    # ============================================================
    # PRODUCT VARIANTS MANAGEMENT
    # ============================================================

    def add_product_variant(self, product_id: str, size: int, color: str,
                            stock: int = 0, image_url: str = None) -> Optional[Dict[str, Any]]:
        """Add a product variant (size/color combination)"""
        try:
            variant_data = {
                'product_id': product_id,
                'size': size,
                'color': color,
                'stock': stock,
                'image_url': image_url
            }
            result = self.client.table('product_variants').insert(variant_data).execute()
            logger.info(f"Added variant for product: {product_id}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error adding variant: {e}")
            return None

    def get_product_variants(self, product_id: str) -> List[Dict[str, Any]]:
        """Get all variants for a product"""
        try:
            result = self.client.table('product_variants').select('*').eq('product_id', product_id).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting variants: {e}")
            return []

    def get_variant(self, variant_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific variant with product details"""
        try:
            result = self.client.table('product_variants').select(
                '*, products(*)'
            ).eq('id', variant_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting variant: {e}")
            return None

    def update_variant_stock(self, variant_id: str, stock: int) -> bool:
        """Update stock for a variant"""
        try:
            result = self.client.table('product_variants').update(
                {'stock': stock, 'updated_at': self._get_current_time()}
            ).eq('id', variant_id).execute()
            logger.info(f"Updated stock for variant: {variant_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating stock: {e}")
            return False

    # ============================================================
    # CART MANAGEMENT
    # ============================================================

    def add_to_cart(self, user_id: str, variant_id: str, quantity: int = 1) -> Optional[Dict[str, Any]]:
        """Add item to cart"""
        try:
            # Check if item already in cart
            existing = self.client.table('cart_items').select('*').eq('user_id', user_id).eq('variant_id', variant_id).execute()

            if existing.data:
                # Update quantity
                new_quantity = existing.data[0]['quantity'] + quantity
                result = self.client.table('cart_items').update(
                    {'quantity': new_quantity, 'updated_at': self._get_current_time()}
                ).eq('id', existing.data[0]['id']).execute()
                return result.data[0] if result.data else None

            # Add new item
            cart_data = {
                'user_id': user_id,
                'variant_id': variant_id,
                'quantity': quantity
            }
            result = self.client.table('cart_items').insert(cart_data).execute()
            logger.info(f"Added item to cart for user: {user_id}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error adding to cart: {e}")
            return None

    def get_cart_items(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all cart items for a user with product details"""
        try:
            result = self.client.table('cart_items').select(
                '*, product_variants(*, products(*))'
            ).eq('user_id', user_id).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting cart: {e}")
            return []

    def update_cart_item_quantity(self, cart_item_id: str, quantity: int) -> bool:
        """Update quantity of cart item"""
        try:
            result = self.client.table('cart_items').update(
                {'quantity': quantity, 'updated_at': self._get_current_time()}
            ).eq('id', cart_item_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error updating cart quantity: {e}")
            return False

    def remove_from_cart(self, cart_item_id: str) -> bool:
        """Remove item from cart"""
        try:
            result = self.client.table('cart_items').delete().eq('id', cart_item_id).execute()
            return True
        except Exception as e:
            logger.error(f"Error removing from cart: {e}")
            return False

    def clear_cart(self, user_id: str) -> bool:
        """Clear all items from user's cart"""
        try:
            result = self.client.table('cart_items').delete().eq('user_id', user_id).execute()
            logger.info(f"Cleared cart for user: {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error clearing cart: {e}")
            return False

    # ============================================================
    # PROMO CODE MANAGEMENT
    # ============================================================

    def validate_promo_code(self, code: str, order_amount: int) -> Optional[Dict[str, Any]]:
        """Validate and get promo code details"""
        try:
            result = self.client.table('promo_codes').select('*').eq('code', code).eq('is_active', True).execute()

            if not result.data:
                return None

            promo = result.data[0]

            # Check expiration
            if promo.get('expires_at'):
                expires = datetime.fromisoformat(promo['expires_at'].replace('Z', '+00:00'))
                if datetime.now(expires.tzinfo) > expires:
                    return None

            # Check usage limit
            if promo.get('max_uses') and promo['current_uses'] >= promo['max_uses']:
                return None

            # Check minimum order amount
            if promo.get('min_order_amount', 0) > order_amount:
                return None

            return promo
        except Exception as e:
            logger.error(f"Error validating promo code: {e}")
            return None

    def apply_promo_code(self, promo_id: str) -> bool:
        """Increment promo code usage"""
        try:
            result = self.client.table('promo_codes').select('current_uses').eq('id', promo_id).execute()
            if result.data:
                new_uses = result.data[0]['current_uses'] + 1
                self.client.table('promo_codes').update({'current_uses': new_uses, 'updated_at': self._get_current_time()}).eq('id', promo_id).execute()
                return True
            return False
        except Exception as e:
            logger.error(f"Error applying promo code: {e}")
            return None

    # ============================================================
    # ORDER MANAGEMENT
    # ============================================================

    def create_order(self, user_id: str, items: List[Dict[str, Any]], subtotal: int,
                     delivery_fee: int, discount_amount: int, total_amount: int,
                     shipping_address_id: str, contact_phone: str, promo_code_id: str = None) -> Optional[Dict[str, Any]]:
        """Create a new order"""
        try:
            order_data = {
                'user_id': user_id,
                'subtotal': subtotal,
                'delivery_fee': delivery_fee,
                'discount_amount': discount_amount,
                'total_amount': total_amount,
                'shipping_address_id': shipping_address_id,
                'contact_phone': contact_phone,
                'order_status': 'pending',
                'promo_code_id': promo_code_id
            }
            result = self.client.table('orders').insert(order_data).execute()

            if not result.data:
                return None

            order = result.data[0]

            # Add order items
            for item in items:
                order_item = {
                    'order_id': order['id'],
                    'product_name': item['product_name'],
                    'size': item['size'],
                    'color': item['color'],
                    'quantity': item['quantity'],
                    'price_per_unit': item['price_per_unit']
                }
                self.client.table('order_items').insert(order_item).execute()

            logger.info(f"Created order: {order['id']}")
            return order
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None

    def get_orders(self, user_id: str = None, status: str = None) -> List[Dict[str, Any]]:
        """Get orders with optional filters"""
        try:
            query = self.client.table('orders').select('*, users(*), user_addresses(*)')

            if user_id:
                query = query.eq('user_id', user_id)
            if status:
                query = query.eq('order_status', status)

            result = query.order('created_at', desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return []

    def get_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order details with items"""
        try:
            order_result = self.client.table('orders').select(
                '*, users(*), user_addresses(*)'
            ).eq('id', order_id).execute()
            items_result = self.client.table('order_items').select('*').eq('order_id', order_id).execute()

            if not order_result.data:
                return None

            order = order_result.data[0]
            order['items'] = items_result.data if items_result.data else []
            return order
        except Exception as e:
            logger.error(f"Error getting order: {e}")
            return None

    def update_order_status(self, order_id: str, status: str) -> bool:
        """Update order status"""
        try:
            valid_statuses = ['pending', 'confirmed', 'shipped', 'delivered', 'cancelled']
            if status not in valid_statuses:
                logger.error(f"Invalid status: {status}")
                return False

            result = self.client.table('orders').update(
                {'order_status': status, 'updated_at': self._get_current_time()}
            ).eq('id', order_id).execute()
            logger.info(f"Updated order {order_id} status to {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating order status: {e}")
            return False

    # ============================================================
    # PAYMENT MANAGEMENT
    # ============================================================

    def create_payment(self, order_id: str, payment_method: str, transaction_reference: str) -> Optional[Dict[str, Any]]:
        """Create a payment record"""
        try:
            payment_data = {
                'order_id': order_id,
                'payment_method': payment_method,
                'transaction_reference': transaction_reference,
                'is_verified': False
            }
            result = self.client.table('payments').insert(payment_data).execute()
            logger.info(f"Created payment for order: {order_id}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating payment: {e}")
            return None

    def verify_payment(self, payment_id: str, admin_telegram_id: int) -> bool:
        """Verify a payment (admin only)"""
        try:
            update_data = {
                'is_verified': True,
                'verified_by_admin_id': admin_telegram_id,
                'verified_at': self._get_current_time(),
                'updated_at': self._get_current_time()
            }
            result = self.client.table('payments').update(update_data).eq('id', payment_id).execute()
            logger.info(f"Payment {payment_id} verified by admin {admin_telegram_id}")
            return True
        except Exception as e:
            logger.error(f"Error verifying payment: {e}")
            return False

    def get_payment_by_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get payment for an order"""
        try:
            result = self.client.table('payments').select('*').eq('order_id', order_id).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error getting payment: {e}")
            return None

    # ============================================================
    # REVIEW MANAGEMENT
    # ============================================================

    def add_review(self, user_id: str, product_id: str, rating: int, comment: str = None) -> Optional[Dict[str, Any]]:
        """Add a product review"""
        try:
            review_data = {
                'user_id': user_id,
                'product_id': product_id,
                'rating': rating,
                'comment': comment
            }
            result = self.client.table('product_reviews').upsert(review_data).execute()
            logger.info(f"Added review for product: {product_id}")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error adding review: {e}")
            return None

    def get_product_reviews(self, product_id: str) -> List[Dict[str, Any]]:
        """Get all reviews for a product"""
        try:
            result = self.client.table('product_reviews').select(
                '*, users(*)'
            ).eq('product_id', product_id).order('created_at', desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            logger.error(f"Error getting reviews: {e}")
            return []


# Initialize global database manager
db = DatabaseManager()