import os
from supabase import create_client, Client
from dotenv import load_dotenv
import logging

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Supabase Configuration (ከ .env ፋይል ውስጥ ያነባል)
SUPABASE_URL = os.getenv('VITE_SUPABASE_URL')
SUPABASE_KEY = os.getenv('VITE_SUPABASE_ANON_KEY')

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase configuration. Check .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ============================================================
# Telegram Bot የሚፈልጋቸው ፈንክሽኖች (ከዳሽቦርዱ ሰንጠረዥ ጋር የተናበቡ)
# ============================================================

def get_products_by_category(category_name):
    """ምርቶችን ከነ ሳይዛቸው እና ዋጋቸው ከ Supabase ያወጣል"""
    try:
        # በምድብ (Category) መሰረት ምርቶችን መፈለግ
        result = supabase.table('products').select('*, product_variants(*)').eq('category', category_name).eq('is_active', True).execute()
        
        # ቦቱ በሚፈልገው ፎርማት (Dict) አዘጋጅቶ መመለስ
        formatted_products = []
        for p in result.data:
            # ቫሪያንት (ሳይዝ እና ስቶክ) ካለው የመጀመሪያውን ይወስዳል
            variants = p.get('product_variants', [])
            size = variants[0].get('size', 'N/A') if variants else 'N/A'
            stock = variants[0].get('stock', '0') if variants else '0'
            photo = variants[0].get('image_url', None) if variants else None
            
            formatted_products.append({
                'id': p['id'],
                'name': p['name'],
                'price': p['base_price'], # ዳታቤዝህ ላይ 'base_price' ስለሆነ
                'size': size,
                'stock': stock,
                'photo': photo
            })
        return formatted_products
    except Exception as e:
        logger.error(f"Error fetching products: {e}")
        return []

def get_user_orders(chat_id):
    """የአንድን ደንበኛ ትዕዛዞች ከ Supabase ያወጣል"""
    try:
        # መጀመሪያ ተጠቃሚውን በ Telegram ID እንፈልገዋለን
        user_res = supabase.table('users').select('id').eq('telegram_id', chat_id).execute()
        if not user_res.data:
            return []
        
        user_uuid = user_res.data[0]['id']
        # ትዕዛዞቹን መፈለግ
        result = supabase.table('orders').select('*').eq('user_id', user_uuid).execute()
        
        return [{
            'order_id': o['id'][:8], # UUID ውን አሳጥሮ ለማሳየት
            'product_name': "ጫማ (የታዘዘ)", # እንደ አስፈላጊነቱ ማስተካከል ይቻላል
            'status': o['order_status']
        } for o in result.data]
    except Exception as e:
        logger.error(f"Error fetching user orders: {e}")
        return []

def get_all_orders():
    """ሁሉንም የገቡ ትዕዛዞች ለአድሚን ያሳያል"""
    try:
        result = supabase.table('orders').select('*, users(*)').execute()
        return [{
            'order_id': o['id'][:8],
            'user_name': o['users']['first_name'] if o.get('users') else "Unknown",
            'product_name': "ጫማ",
            'phone': o['contact_phone'],
            'status': o['order_status']
        } for o in result.data]
    except Exception as e:
        logger.error(f"Error fetching all orders: {e}")
        return []