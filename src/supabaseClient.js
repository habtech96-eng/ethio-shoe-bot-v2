import { createClient } from '@supabase/supabase-js';

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseKey) {
  throw new Error('Missing Supabase environment variables');
}

export const supabase = createClient(supabaseUrl, supabaseKey);

// Database helper functions
export const db = {
  // Products
  async getProducts(category = null) {
    let query = supabase
      .from('products')
      .select('*, product_variants(*)')
      .eq('is_active', true)
      .order('created_at', { ascending: false });

    if (category) {
      query = query.eq('category', category);
    }

    const { data, error } = await query;
    if (error) throw error;
    return data;
  },

  async getProduct(id) {
    const { data, error } = await supabase
      .from('products')
      .select('*, product_variants(*)')
      .eq('id', id)
      .single();
    if (error) throw error;
    return data;
  },

  async createProduct(product) {
    const { data, error } = await supabase
      .from('products')
      .insert(product)
      .select()
      .single();
    if (error) throw error;
    return data;
  },

  async updateProduct(id, updates) {
    const { data, error } = await supabase
      .from('products')
      .update({ ...updates, updated_at: new Date().toISOString() })
      .eq('id', id)
      .select()
      .single();
    if (error) throw error;
    return data;
  },

  async deleteProduct(id) {
    const { data, error } = await supabase
      .from('products')
      .update({ is_active: false })
      .eq('id', id);
    if (error) throw error;
    return data;
  },

  // Product Variants
  async addVariant(variant) {
    const { data, error } = await supabase
      .from('product_variants')
      .insert(variant)
      .select()
      .single();
    if (error) throw error;
    return data;
  },

  async updateVariantStock(id, stock) {
    const { data, error } = await supabase
      .from('product_variants')
      .update({ stock, updated_at: new Date().toISOString() })
      .eq('id', id);
    if (error) throw error;
    return data;
  },

  // Orders
  async getOrders(status = null) {
    let query = supabase
      .from('orders')
      .select('*, users(*), user_addresses(*), order_items(*)')
      .order('created_at', { ascending: false });

    if (status) {
      query = query.eq('order_status', status);
    }

    const { data, error } = await query;
    if (error) throw error;
    return data;
  },

  async updateOrderStatus(id, status) {
    const { data, error } = await supabase
      .from('orders')
      .update({ order_status: status, updated_at: new Date().toISOString() })
      .eq('id', id)
      .select()
      .single();
    if (error) throw error;
    return data;
  },

  // Payments
  async getPayments() {
    const { data, error } = await supabase
      .from('payments')
      .select('*, orders(*)')
      .order('created_at', { ascending: false });
    if (error) throw error;
    return data;
  },

  async verifyPayment(id, adminId) {
    const { data, error } = await supabase
      .from('payments')
      .update({
        is_verified: true,
        verified_by_admin_id: adminId,
        verified_at: new Date().toISOString()
      })
      .eq('id', id)
      .select()
      .single();
    if (error) throw error;
    return data;
  },

  // Promo Codes
  async getPromoCodes() {
    const { data, error } = await supabase
      .from('promo_codes')
      .select('*')
      .order('created_at', { ascending: false });
    if (error) throw error;
    return data;
  },

  async createPromoCode(promo) {
    const { data, error } = await supabase
      .from('promo_codes')
      .insert(promo)
      .select()
      .single();
    if (error) throw error;
    return data;
  },

  // Reviews
  async getReviews(productId) {
    const { data, error } = await supabase
      .from('product_reviews')
      .select('*, users(*)')
      .eq('product_id', productId)
      .order('created_at', { ascending: false });
    if (error) throw error;
    return data;
  }
};
