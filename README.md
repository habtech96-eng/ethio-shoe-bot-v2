# Ethio Shoe Store - Enterprise E-Commerce Platform

**Premium Ethiopian Footwear E-Commerce Solution with PostgreSQL/Supabase Backend**

## 🎯 Project Overview

This is a complete enterprise-grade e-commerce platform for an Ethiopian shoe store, rebuilt from SQLite to PostgreSQL using Supabase. The system features a comprehensive database architecture with 10 interconnected tables, full Row Level Security (RLS), and a modern React admin dashboard.

### Key Features

- ✅ **PostgreSQL/Supabase Backend** - Replaced SQLite with production-grade PostgreSQL
- ✅ **10 Database Tables** - Complete relational schema with proper foreign keys
- ✅ **Row Level Security** - All tables protected with RLS policies
- ✅ **React Admin Dashboard** - Modern web interface for managing products, orders, and payments
- ✅ **Telegram Bot Integration** - Customer-facing bot for shopping
- ✅ **Multi-Language Support** - Amharic + English interface
- ✅ **Payment Integration** - Telebirr and CBE bank support
- ✅ **Inventory Management** - Variant-based stock control (size/color)

## 📊 Database Schema

### 10 Enterprise-Grade Tables

1. **`users`** - Customer profiles with Telegram integration
   - UUID primary key
   - Unique telegram_id for user identification
   - Phone number and registration tracking

2. **`user_addresses`** - Multiple shipping addresses
   - Support for Ethiopian cities (Addis Ababa, Adama, Hawassa, etc.)
   - Default address flag for quick checkout
   - Cascade delete with user

3. **`products`** - Advanced product catalog
   - Categories: የወንዶች (Men), የሴቶች (Women), የህፃናት (Kids), Unisex
   - Brands: Nike, Adidas, Puma, Reebok, Jordan, Local
   - Discount pricing with original/base price display

4. **`product_variants`** - Granular stock control
   - Size tracking (35-50)
   - Color variants
   - Individual stock per variant
   - Image URLs per variant

5. **`cart_items`** - Persistent shopping cart
   - User-variant relationships
   - Quantity tracking
   - Cascade deletions

6. **`promo_codes`** - Discount and marketing system
   - Percentage or flat amount discounts
   - Minimum order requirements
   - Usage limits with expiration dates

7. **`orders`** - Complete order lifecycle
   - Status tracking: pending → confirmed → shipped → delivered
   - Price breakdown (subtotal, delivery, discount, total)
   - Shipping address reference
   - Promo code integration

8. **`order_items`** - Historical snapshots
   - Product details captured at order time
   - Price history preservation
   - Size/color/quantity tracking

9. **`payments`** - Payment audit trails
   - Telebirr and CBE payment methods
   - Transaction reference tracking
   - Admin verification workflow
   - Timestamped verification

10. **`product_reviews`** - Social proof
    - 1-5 star ratings
    - User comments
    - One review per user per product

## 🔒 Security Features

### Row Level Security (RLS)

All tables have RLS enabled with restrictive policies:

- **User Data**: Users can only access their own records
- **Admin Access**: Whitelisted admin Telegram IDs have elevated access
- **Product Data**: Active products are publicly viewable
- **Payment Verification**: Only admins can verify payments
- **Order Management**: Customers view their orders; admins see all

### Helper Functions

```sql
-- Check if user is admin
is_admin(telegram_id) → BOOLEAN
```

## 🛠️ Tech Stack

### Backend
- **Python 3.10+**
- **pyTelegramBotAPI 4.14.0** - Telegram bot framework
- **Supabase Python Client 2.4.3** - PostgreSQL ORM
- **Flask** - Keep-alive web server for hosting

### Frontend
- **React 19.2.6** - Admin dashboard
- **Vite 8.0.14** - Build tool
- **Tailwind CSS** - Styling
- **Lucide React** - Icons
- **Supabase JS Client** - Database operations

### Database
- **PostgreSQL** via Supabase
- **Row Level Security** enabled
- **Proper foreign keys** with CASCADE rules

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- Node.js 18 or higher
- Supabase account (already configured)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/habtech96-eng/ethio-shoe-store-bot.git
   cd ethio-shoe-store-bot
   ```

2. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Node.js dependencies**
   ```bash
   npm install
   ```

4. **Set up environment variables**
   
   Already configured in `.env`:
   ```
   VITE_SUPABASE_URL=https://0ec90b57d6e95fcbda19832f.supabase.co
   VITE_SUPABASE_ANON_KEY=eyJhbGc... (configured)
   ```

5. **Run database migrations**
   
   Migrations already applied:
   - `001_comprehensive_shoe_store_schema` - All 10 tables
   - `002_row_level_security_policies` - RLS policies

### Running the Application

#### Telegram Bot
```bash
python bot.py
```

#### React Admin Dashboard
```bash
npm run dev
```

Access admin dashboard at: http://localhost:3000

#### Production Build
```bash
npm run build
```

## 📱 Bot Commands

### Customer Commands
- `/start` - Register and view main menu
- `/cart` - View shopping cart
- `👟 ምርቶችን እይ` - Browse products by category
- `🛍️ የእኔ ትዕዛዞች` - View order history

### Admin Commands
- `🔐 Admin Panel` - Access admin dashboard
- Add products with variants
- View and update order status
- Verify payments

## 🔐 Security Credentials

### Bot Configuration
```
BOT_TOKEN = "8651460654:AAG9S_BOfqvf0QhUupDCiMrXVc4yLdOj3Uw"
ADMIN_IDS = [7098279917]
```

**🔐 IMPORTANT**: These credentials are actively maintained as requested.

## 💰 Pricing Display

All prices are displayed in **Ethiopian Birr (ETB/ብር)** with high-contrast formatting:

- Regular price: `2,500 ETB (ብር)`
- Discount price: `~~3,000~~ **2,500 ETB (ብር)**`

## 🎨 Design System

### High-Contrast Color Palette

All UI elements follow strict contrast rules:

- **Primary**: `#1a202c` (Dark Gray) - Text on light backgrounds
- **Secondary**: `#2d3748` (Medium Gray)
- **Accent**: `#3182ce` (Blue) - CTAs and highlights
- **Success**: `#25855a` (Green) - Verified/completed status
- **Warning**: `#d69e2e` (Yellow) - Pending status
- **Error**: `#c53030` (Red) - Cancelled/rejected status

### Status Badges

- ⏱️ **Pending**: Yellow background, dark text
- ✅ **Confirmed**: Teal background, dark text
- 🚚 **Shipped**: Blue background, dark text
- 📦 **Delivered**: Green background, dark text
- ❌ **Cancelled**: Red background, dark text

## 📊 Database Metrics

Check live status at:
```
https://supabase.com/dashboard/project/_/editor
```

All tables created:
- ✅ users
- ✅ user_addresses
- ✅ products
- ✅ product_variants
- ✅ cart_items
- ✅ promo_codes
- ✅ orders
- ✅ order_items
- ✅ payments
- ✅ product_reviews

## 🔧 API Reference

### Database Manager Methods

```python
# User Management
db.create_user(telegram_id, first_name, username, phone)
db.get_user(telegram_id)
db.get_user_by_id(user_id)

# Address Management
db.add_address(user_id, city, subcity, location, is_default)
db.get_user_addresses(user_id)

# Product Management
db.add_product(name, category, base_price, description, brand, original_price)
db.get_products_by_category(category)
db.get_product(product_id)
db.update_product(product_id, update_data)

# Variant Management
db.add_product_variant(product_id, size, color, stock, image_url)
db.get_variant(variant_id)
db.update_variant_stock(variant_id, stock)

# Cart Management
db.add_to_cart(user_id, variant_id, quantity)
db.get_cart_items(user_id)
db.clear_cart(user_id)

# Order Management
db.create_order(user_id, items, subtotal, delivery_fee, ...)
db.get_orders(user_id, status)
db.update_order_status(order_id, status)

# Payment Management
db.create_payment(order_id, payment_method, transaction_ref)
db.verify_payment(payment_id, admin_telegram_id)
```

## 📝 License

MIT License - Ethiopian Shoe Store 2024

## 👨‍💻 Author

**habtech96-eng**
GitHub: https://github.com/habtech96-eng

## 🙏 Acknowledgments

- Ethiopian coding community
- Telegram Bot API
- Supabase team
- React and Vite teams

---

**Built with ❤️ for Ethiopian Commerce**
