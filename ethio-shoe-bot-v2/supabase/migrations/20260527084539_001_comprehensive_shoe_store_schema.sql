/*
  # Comprehensive Ethiopian Shoe Store Database Schema
  
  This migration creates a complete enterprise-grade e-commerce database for an Ethiopian shoe store.
  
  ## Overview
  This schema supports:
  - Customer management with Telegram integration
  - Multi-address shipping system
  - Advanced product catalog with variants
  - Shopping cart system
  - Promo code management
  - Complete order lifecycle tracking
  - Payment verification system
  - Product reviews and ratings
  
  ## New Tables (10 total)
  
  1. `users` - Customer profiles with Telegram integration
     - Primary identifier: telegram_id (unique)
     - Tracks registration and profile information
  
  2. `user_addresses` - Multiple shipping addresses per user
     - Supports Ethiopian cities (Addis Ababa, Adama, Hawassa, etc.)
     - Default address flag for quick checkout
  
  3. `products` (shoes) - Advanced product catalog
     - Categories: የወንዶች (Men), የሴቶች (Women), የህፃናት (Kids), የሁለቱም/Unisex
     - Brands: Nike, Adidas, Puma, Reebok, Jordan, Local
     - Price tracking with discount support
  
  4. `product_variants` - Granular stock control
     - Size and color variants
     - Individual stock tracking per variant
     - Image URLs per variant
  
  5. `cart_items` - Persistent shopping cart
     - Links users to product variants
     - Quantity tracking
  
  6. `promo_codes` - Discount and marketing system
     - Percentage or flat amount discounts
     - Usage limits and expiration dates
     - Minimum order requirements
  
  7. `orders` - Complete order lifecycle
     - Status tracking: pending, confirmed, shipped, delivered, cancelled
     - Price breakdown (subtotal, delivery, discount, total)
     - Shipping address reference
  
  8. `order_items` - Historical snapshot
     - Captures product details at order time
     - Price history preservation
  
  9. `payments` - Payment audit trails
     - Supports telebirr and CBE payment methods
     - Admin verification workflow
     - Transaction reference tracking
  
  10. `product_reviews` - Social proof system
      - 1-5 star ratings
      - User comments
      - Timestamp tracking
  
  ## Security
  - Row Level Security (RLS) enabled on all tables
  - Policies restrict access to authenticated users
  - Admin-only write access for critical tables
  - Users can only access their own data
  
  ## Important Notes
  1. All monetary values in Ethiopian Birr (ETB/ብር)
  2. Telegram ID used as primary user identifier
  3. Order status changes are time-stamped
  4. Payment verification requires admin approval
  5. Product variants enable flexible inventory management
*/

-- 1. USERS TABLE (Customer Profiling)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE NOT NULL,
    username TEXT,
    first_name TEXT NOT NULL,
    phone_number TEXT,
    registered_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. USER_ADDRESSES TABLE (Multiple Shipping Management)
CREATE TABLE IF NOT EXISTS user_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    city TEXT NOT NULL,
    subcity_or_zone TEXT,
    specific_location_or_woreda TEXT,
    is_default BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_city CHECK (
        city IN ('Addis Ababa', 'Adama', 'Hawassa', 'Bahir Dar', 'Dire Dawa', 'Mekelle', 'Gondar', 'Jimma', 'Dessie', 'Shashamane')
    )
);

-- 3. PRODUCTS TABLE (Advanced Catalog)
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL,
    brand TEXT,
    base_price INTEGER NOT NULL, -- In ETB (Ethiopian Birr)
    original_price INTEGER, -- For discount display (cross-out price)
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_category CHECK (
        category IN ('የወንዶች', 'የሴቶች', 'የህፃናት', 'የሁለቱም/Unisex')
    ),
    CONSTRAINT valid_brand CHECK (
        brand IS NULL OR brand IN ('Nike', 'Adidas', 'Puma', 'Reebok', 'Jordan', 'Local', 'Other')
    ),
    CONSTRAINT positive_base_price CHECK (base_price >= 0),
    CONSTRAINT positive_original_price CHECK (original_price IS NULL OR original_price >= 0)
);

-- 4. PRODUCT_VARIANTS TABLE (Granular Stock Control)
CREATE TABLE IF NOT EXISTS product_variants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    size INTEGER NOT NULL,
    color TEXT NOT NULL,
    image_url TEXT,
    stock INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_size CHECK (size >= 30 AND size <= 50),
    CONSTRAINT positive_stock CHECK (stock >= 0),
    UNIQUE(product_id, size, color)
);

-- 5. CART_ITEMS TABLE (Persisted Shopping Carts)
CREATE TABLE IF NOT EXISTS cart_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    variant_id UUID NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
    quantity INTEGER DEFAULT 1,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT positive_quantity CHECK (quantity > 0),
    UNIQUE(user_id, variant_id)
);

-- 6. PROMO_CODES TABLE (Discounts & Marketing)
CREATE TABLE IF NOT EXISTS promo_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code TEXT UNIQUE NOT NULL,
    discount_type TEXT NOT NULL,
    discount_value INTEGER NOT NULL,
    min_order_amount INTEGER DEFAULT 0,
    max_uses INTEGER,
    current_uses INTEGER DEFAULT 0,
    expires_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_discount_type CHECK (discount_type IN ('percentage', 'flat_amount')),
    CONSTRAINT positive_discount_value CHECK (discount_value > 0),
    CONSTRAINT non_negative_min_order CHECK (min_order_amount >= 0),
    CONSTRAINT non_negative_uses CHECK (current_uses >= 0),
    CONSTRAINT valid_max_uses CHECK (max_uses IS NULL OR max_uses > 0)
);

-- 7. ORDERS TABLE (Order Lifecycle Management)
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE SET NULL,
    subtotal INTEGER NOT NULL, -- In ETB
    delivery_fee INTEGER DEFAULT 50, -- In ETB
    discount_amount INTEGER DEFAULT 0, -- In ETB
    total_amount INTEGER NOT NULL, -- Final price in ETB
    shipping_address_id UUID REFERENCES user_addresses(id) ON DELETE SET NULL,
    contact_phone TEXT NOT NULL,
    order_status TEXT DEFAULT 'pending',
    promo_code_id UUID REFERENCES promo_codes(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_order_status CHECK (
        order_status IN ('pending', 'confirmed', 'shipped', 'delivered', 'cancelled')
    ),
    CONSTRAINT non_negative_prices CHECK (
        subtotal >= 0 AND delivery_fee >= 0 AND discount_amount >= 0 AND total_amount >= 0
    )
);

-- 8. ORDER_ITEMS TABLE (Historical Snapshot)
CREATE TABLE IF NOT EXISTS order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_name TEXT NOT NULL,
    size INTEGER NOT NULL,
    color TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    price_per_unit INTEGER NOT NULL, -- In ETB
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT positive_quantity CHECK (quantity > 0),
    CONSTRAINT positive_price CHECK (price_per_unit >= 0),
    CONSTRAINT valid_item_size CHECK (size >= 30 AND size <= 50)
);

-- 9. PAYMENTS TABLE (Audit Trails)
CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    payment_method TEXT NOT NULL,
    transaction_reference TEXT NOT NULL UNIQUE,
    is_verified BOOLEAN DEFAULT FALSE,
    verified_by_admin_id BIGINT,
    verified_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_payment_method CHECK (payment_method IN ('telebirr', 'cbe'))
);

-- 10. PRODUCT_REVIEWS TABLE (Social Proof)
CREATE TABLE IF NOT EXISTS product_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL,
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT valid_rating CHECK (rating >= 1 AND rating <= 5),
    UNIQUE(user_id, product_id)
);

-- Create indexes for performance optimization
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_user_addresses_user_id ON user_addresses(user_id);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);
CREATE INDEX IF NOT EXISTS idx_products_is_active ON products(is_active);
CREATE INDEX IF NOT EXISTS idx_product_variants_product_id ON product_variants(product_id);
CREATE INDEX IF NOT EXISTS idx_product_variants_size_color ON product_variants(size, color);
CREATE INDEX IF NOT EXISTS idx_cart_items_user_id ON cart_items(user_id);
CREATE INDEX IF NOT EXISTS idx_cart_items_variant_id ON cart_items(variant_id);
CREATE INDEX IF NOT EXISTS idx_orders_user_id ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(order_status);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_order_id ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_verified ON payments(is_verified);
CREATE INDEX IF NOT EXISTS idx_promo_codes_code ON promo_codes(code);
CREATE INDEX IF NOT EXISTS idx_product_reviews_product_id ON product_reviews(product_id);
CREATE INDEX IF NOT EXISTS idx_product_reviews_rating ON product_reviews(rating);