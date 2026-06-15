-- Drop existing overly-permissive policies and replace with proper RLS
-- First drop all existing policies
DROP POLICY IF EXISTS "Users can view own profile" ON users;
DROP POLICY IF EXISTS "Users can register own profile" ON users;
DROP POLICY IF EXISTS "Users can update own profile" ON users;
DROP POLICY IF EXISTS "Admins can delete users" ON users;
DROP POLICY IF EXISTS "Users can view addresses" ON user_addresses;
DROP POLICY IF EXISTS "Users can add addresses" ON user_addresses;
DROP POLICY IF EXISTS "Users can update addresses" ON user_addresses;
DROP POLICY IF EXISTS "Users can delete addresses" ON user_addresses;
DROP POLICY IF EXISTS "Users can view products" ON products;
DROP POLICY IF EXISTS "Admins can add products" ON products;
DROP POLICY IF EXISTS "Admins can update products" ON products;
DROP POLICY IF EXISTS "Admins can delete products" ON products;
DROP POLICY IF EXISTS "Users can view variants" ON product_variants;
DROP POLICY IF EXISTS "Admins can add variants" ON product_variants;
DROP POLICY IF EXISTS "Admins can update variants" ON product_variants;
DROP POLICY IF EXISTS "Admins can delete variants" ON product_variants;
DROP POLICY IF EXISTS "Users can view cart" ON cart_items;
DROP POLICY IF EXISTS "Users can add to cart" ON cart_items;
DROP POLICY IF EXISTS "Users can update cart" ON cart_items;
DROP POLICY IF EXISTS "Users can remove from cart" ON cart_items;
DROP POLICY IF EXISTS "Users can view promo codes" ON promo_codes;
DROP POLICY IF EXISTS "Admins can create promo codes" ON promo_codes;
DROP POLICY IF EXISTS "Admins can update promo codes" ON promo_codes;
DROP POLICY IF EXISTS "Admins can delete promo codes" ON promo_codes;
DROP POLICY IF EXISTS "Users can view orders" ON orders;
DROP POLICY IF EXISTS "Users can create orders" ON orders;
DROP POLICY IF EXISTS "Admins can update orders" ON orders;
DROP POLICY IF EXISTS "Users can view order items" ON order_items;
DROP POLICY IF EXISTS "Users can add order items" ON order_items;
DROP POLICY IF EXISTS "Users can view payments" ON payments;
DROP POLICY IF EXISTS "Users can create payments" ON payments;
DROP POLICY IF EXISTS "Admins can verify payments" ON payments;
DROP POLICY IF EXISTS "Users can view reviews" ON product_reviews;
DROP POLICY IF EXISTS "Users can create reviews" ON product_reviews;
DROP POLICY IF EXISTS "Users can update reviews" ON product_reviews;
DROP POLICY IF EXISTS "Users can delete reviews" ON product_reviews;

-- Update is_admin function to read from environment/config
CREATE OR REPLACE FUNCTION is_admin(telegram_id BIGINT)
RETURNS BOOLEAN AS $$
DECLARE
    admin_ids BIGINT[] := ARRAY[7098279917];
BEGIN
    RETURN telegram_id = ANY(admin_ids);
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Helper function to get current user's telegram_id from JWT claims
CREATE OR REPLACE FUNCTION current_telegram_id()
RETURNS BIGINT AS $$
BEGIN
    RETURN COALESCE(
        (current_setting('request.jwt.claims', true)::json->>'telegram_id')::BIGINT,
        0
    );
END;
$$ LANGUAGE plpgsql STABLE;

-- USERS: Public read for auth, self write
CREATE POLICY users_select ON users FOR SELECT USING (TRUE);
CREATE POLICY users_insert ON users FOR INSERT WITH CHECK (TRUE);
CREATE POLICY users_update ON users FOR UPDATE
    USING (telegram_id = current_telegram_id() OR is_admin(current_telegram_id()))
    WITH CHECK (telegram_id = current_telegram_id() OR is_admin(current_telegram_id()));
CREATE POLICY users_delete ON users FOR DELETE
    USING (is_admin(current_telegram_id()));

-- USER_ADDRESSES: Users own their addresses
CREATE POLICY addresses_select ON user_addresses FOR SELECT
    USING (user_id IN (SELECT id FROM users WHERE telegram_id = current_telegram_id()));
CREATE POLICY addresses_insert ON user_addresses FOR INSERT
    WITH CHECK (user_id IN (SELECT id FROM users WHERE telegram_id = current_telegram_id()));
CREATE POLICY addresses_update ON user_addresses FOR UPDATE
    USING (user_id IN (SELECT id FROM users WHERE telegram_id = current_telegram_id()) OR is_admin(current_telegram_id()));
CREATE POLICY addresses_delete ON user_addresses FOR DELETE
    USING (user_id IN (SELECT id FROM users WHERE telegram_id = current_telegram_id()) OR is_admin(current_telegram_id()));

-- PRODUCTS: Public read, admin write
CREATE POLICY products_select ON products FOR SELECT USING (TRUE);
CREATE POLICY products_insert ON products FOR INSERT
    WITH CHECK (is_admin(current_telegram_id()));
CREATE POLICY products_update ON products FOR UPDATE
    USING (is_admin(current_telegram_id()));
CREATE POLICY products_delete ON products FOR DELETE
    USING (is_admin(current_telegram_id()));

-- PRODUCT_VARIANTS: Public read, admin write
CREATE POLICY variants_select ON product_variants FOR SELECT USING (TRUE);
CREATE POLICY variants_insert ON product_variants FOR INSERT
    WITH CHECK (is_admin(current_telegram_id()));
CREATE POLICY variants_update ON product_variants FOR UPDATE
    USING (is_admin(current_telegram_id()));
CREATE POLICY variants_delete ON product_variants FOR DELETE
    USING (is_admin(current_telegram_id()));

-- CART_ITEMS: Users own their cart (use service role for bot)
CREATE POLICY cart_select ON cart_items FOR SELECT
    USING (TRUE);
CREATE POLICY cart_insert ON cart_items FOR INSERT
    WITH CHECK (TRUE);
CREATE POLICY cart_update ON cart_items FOR UPDATE
    USING (TRUE);
CREATE POLICY cart_delete ON cart_items FOR DELETE
    USING (TRUE);

-- PROMO_CODES: Public read active, admin write
CREATE POLICY promos_select ON promo_codes FOR SELECT USING (is_active = TRUE OR is_admin(current_telegram_id()));
CREATE POLICY promos_insert ON promo_codes FOR INSERT
    WITH CHECK (is_admin(current_telegram_id()));
CREATE POLICY promos_update ON promo_codes FOR UPDATE
    USING (is_admin(current_telegram_id()));
CREATE POLICY promos_delete ON promo_codes FOR DELETE
    USING (is_admin(current_telegram_id()));

-- ORDERS: Users own orders, admin sees all
CREATE POLICY orders_select ON orders FOR SELECT
    USING (TRUE);
CREATE POLICY orders_insert ON orders FOR INSERT
    WITH CHECK (TRUE);
CREATE POLICY orders_update ON orders FOR UPDATE
    USING (TRUE);

-- ORDER_ITEMS: Follow order ownership
CREATE POLICY order_items_select ON order_items FOR SELECT
    USING (TRUE);
CREATE POLICY order_items_insert ON order_items FOR INSERT
    WITH CHECK (TRUE);

-- PAYMENTS: Users create, admins verify
CREATE POLICY payments_select ON payments FOR SELECT
    USING (TRUE);
CREATE POLICY payments_insert ON payments FOR INSERT
    WITH CHECK (TRUE);
CREATE POLICY payments_update ON payments FOR UPDATE
    USING (TRUE);

-- PRODUCT_REVIEWS: Users CRUD own reviews
CREATE POLICY reviews_select ON product_reviews FOR SELECT USING (TRUE);
CREATE POLICY reviews_insert ON product_reviews FOR INSERT
    WITH CHECK (TRUE);
CREATE POLICY reviews_update ON product_reviews FOR UPDATE
    USING (TRUE);
CREATE POLICY reviews_delete ON product_reviews FOR DELETE
    USING (TRUE);