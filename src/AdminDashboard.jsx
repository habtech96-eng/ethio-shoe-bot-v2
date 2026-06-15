import React, { useState, useEffect, useCallback } from 'react';
import { supabase } from './supabaseClient';
import {
  ShoppingBag,
  Package,
  Truck,
  CheckCircle,
  XCircle,
  AlertCircle,
  TrendingUp,
  CreditCard,
  ArrowLeft,
  RefreshCw,
  Lock,
  Unlock,
  AlertTriangle,
  DollarSign,
  Plus,
  Upload,
  X,
  Save,
  Camera
} from 'lucide-react';

const ADMIN_ACCESS_CODE = 'ETHIO_ADMIN_2026';

// Strict status colors as specified
const STATUS_CONFIG = {
  pending: {
    label: 'Pending',
    labelAm: 'በመጠባበቅ ላይ',
    color: 'bg-yellow-100 text-yellow-800 border-yellow-500',
    hex: '#d69e2e',
    icon: AlertCircle
  },
  confirmed: {
    label: 'Confirmed',
    labelAm: 'ተረጋግጧል',
    color: 'bg-teal-100 text-teal-800 border-teal-600',
    hex: '#25855a',
    icon: CheckCircle
  },
  shipped: {
    label: 'Shipped',
    labelAm: 'ተልኳል',
    color: 'bg-blue-100 text-blue-800 border-blue-500',
    hex: '#3182ce',
    icon: Truck
  },
  delivered: {
    label: 'Delivered',
    labelAm: 'ተጠናቋል',
    color: 'bg-green-100 text-green-600 border-green-500',
    hex: '#22c55e',
    icon: Package
  },
  cancelled: {
    label: 'Cancelled',
    labelAm: 'ተሰርዟል',
    color: 'bg-red-100 text-red-800 border-red-600',
    hex: '#c53030',
    icon: XCircle
  }
};

// Category labels mapping
const CATEGORY_LABELS = {
  'የወንዶች': 'የወንዶች (Men)',
  'የሴቶች': 'የሴቶች (Women)',
  'የህፃናት': 'የህፃናት (Kids)',
  'የሁለቱም/Unisex': 'ለሁሉም (Unisex)'
};

const BRANDS = ['Nike', 'Adidas', 'Puma', 'Reebok', 'Jordan', 'Local', 'Other'];
const SIZES = Array.from({length: 21}, (_, i) => 30 + i); // 30-50

function AdminDashboard({ onLogout }) {
  const [orders, setOrders] = useState([]);
  const [products, setProducts] = useState([]);
  const [payments, setPayments] = useState([]);
  const [stats, setStats] = useState({
    totalOrders: 0,
    pendingOrders: 0,
    pendingPayments: 0,
    totalRevenue: 0,
    totalProducts: 0,
    lowStockVariants: 0
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [statusFilter, setStatusFilter] = useState('all');
  const [paymentFilter, setPaymentFilter] = useState('all');
  const [activeTab, setActiveTab] = useState('orders');
  const [showAddProduct, setShowAddProduct] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);

  // New product form state
  const [newProduct, setNewProduct] = useState({
    name: '',
    category: '',
    brand: '',
    base_price: '',
    original_price: '',
    description: '',
    variants: [{ size: 38, color: '', stock: 1, image_url: '' }]
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const { data: ordersData, error: ordersError } = await supabase
        .from('orders')
        .select('*, users(first_name, telegram_id), order_items(*), payments(*)')
        .order('created_at', { ascending: false });

      if (ordersError) throw ordersError;

      const { data: productsData, error: productsError } = await supabase
        .from('products')
        .select('id, name, base_price, is_active, category, brand, product_variants(id, stock, size, color, image_url)')
        .eq('is_active', true);

      if (productsError) throw productsError;

      const { data: paymentsData, error: paymentsError } = await supabase
        .from('payments')
        .select('*, orders(total_amount)')
        .order('created_at', { ascending: false });

      if (paymentsError) throw paymentsError;

      setOrders(ordersData || []);
      setProducts(productsData || []);
      setPayments(paymentsData || []);

      const totalRevenue = (ordersData || [])
        .filter(o => o.order_status === 'delivered')
        .reduce((sum, o) => sum + (o.total_amount || 0), 0);

      const pendingPayments = (paymentsData || []).filter(p => !p.is_verified).length;

      const lowStockVariants = (productsData || []).reduce((count, product) => {
        const variants = product.product_variants || [];
        return count + variants.filter(v => (v.stock || 0) < 5).length;
      }, 0);

      setStats({
        totalOrders: ordersData?.length || 0,
        pendingOrders: (ordersData || []).filter(o => o.order_status === 'pending').length,
        pendingPayments,
        totalRevenue,
        totalProducts: productsData?.length || 0,
        lowStockVariants
      });

    } catch (err) {
      console.error('Error loading dashboard data:', err);
      setError('ዳታ መጫን አልተሳካም። እባክዎ እንደገና ይሞክሩ።');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Real-time subscriptions
  useEffect(() => {
    const channel = supabase
      .channel('admin-dashboard')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'orders' }, loadData)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'payments' }, loadData)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'products' }, loadData)
      .subscribe();

    return () => supabase.removeChannel(channel);
  }, [loadData]);

  const handleStatusUpdate = async (orderId, newStatus) => {
    try {
      const { error } = await supabase
        .from('orders')
        .update({ order_status: newStatus, updated_at: new Date().toISOString() })
        .eq('id', orderId);

      if (error) throw error;
      setOrders(prev => prev.map(o => o.id === orderId ? { ...o, order_status: newStatus } : o));
    } catch (err) {
      console.error('Error updating order status:', err);
      alert('ትዕዛዝ ማሻሻል አልተሳካም።');
    }
  };

  const handlePaymentVerify = async (paymentId, verify) => {
    try {
      const payment = payments.find(p => p.id === paymentId);

      const { error } = await supabase
        .from('payments')
        .update({
          is_verified: verify,
          verified_at: verify ? new Date().toISOString() : null
        })
        .eq('id', paymentId);

      if (error) throw error;

      if (payment?.order_id) {
        await supabase
          .from('orders')
          .update({ order_status: verify ? 'confirmed' : 'cancelled' })
          .eq('id', payment.order_id);
      }

      loadData();
    } catch (err) {
      console.error('Error updating payment:', err);
      alert('ክፍያ ማሻሻል አልተሳካም።');
    }
  };

  const uploadImage = async (file) => {
    try {
      setUploadingImage(true);
      const fileExt = file.name.split('.').pop();
      const fileName = `${Date.now()}-${Math.random().toString(36).substring(7)}.${fileExt}`;
      const filePath = `products/${fileName}`;

      const { error: uploadError } = await supabase.storage
        .from('product-images')
        .upload(filePath, file);

      if (uploadError) throw uploadError;

      const { data: { publicUrl } } = supabase.storage
        .from('product-images')
        .getPublicUrl(filePath);

      return publicUrl;
    } catch (err) {
      console.error('Image upload error:', err);
      alert('ምስል መስቀል አልተሳካም።');
      return null;
    } finally {
      setUploadingImage(false);
    }
  };

  const handleImageUpload = async (e, variantIndex) => {
    const file = e.target.files[0];
    if (!file) return;

    const url = await uploadImage(file);
    if (url) {
      const newVariants = [...newProduct.variants];
      newVariants[variantIndex].image_url = url;
      setNewProduct({ ...newProduct, variants: newVariants });
    }
  };

  const addVariant = () => {
    setNewProduct({
      ...newProduct,
      variants: [...newProduct.variants, { size: 38, color: '', stock: 1, image_url: '' }]
    });
  };

  const removeVariant = (index) => {
    if (newProduct.variants.length === 1) return;
    const newVariants = newProduct.variants.filter((_, i) => i !== index);
    setNewProduct({ ...newProduct, variants: newVariants });
  };

  const updateVariant = (index, field, value) => {
    const newVariants = [...newProduct.variants];
    newVariants[index][field] = value;
    setNewProduct({ ...newProduct, variants: newVariants });
  };

  const handleCreateProduct = async () => {
    try {
      if (!newProduct.name || !newProduct.category || !newProduct.base_price) {
        alert('እባክዎ ሁሉም አስፈላጊ መረጃዎችን ይሙሉ።');
        return;
      }

      // Create product
      const { data: productData, error: productError } = await supabase
        .from('products')
        .insert({
          name: newProduct.name,
          category: newProduct.category,
          brand: newProduct.brand || null,
          base_price: parseInt(newProduct.base_price),
          original_price: newProduct.original_price ? parseInt(newProduct.original_price) : null,
          description: newProduct.description || null,
          is_active: true
        })
        .select()
        .single();

      if (productError) throw productError;

      // Create variants
      for (const variant of newProduct.variants) {
        if (!variant.color || !variant.stock) continue;

        const { error: variantError } = await supabase
          .from('product_variants')
          .insert({
            product_id: productData.id,
            size: parseInt(variant.size),
            color: variant.color,
            stock: parseInt(variant.stock),
            image_url: variant.image_url || null
          });

        if (variantError) console.error('Variant error:', variantError);
      }

      // Reset form
      setNewProduct({
        name: '',
        category: '',
        brand: '',
        base_price: '',
        original_price: '',
        description: '',
        variants: [{ size: 38, color: '', stock: 1, image_url: '' }]
      });
      setShowAddProduct(false);
      loadData();
      alert('ምርት በተሳካ ሁኔታ ተፈጥሯል!');
    } catch (err) {
      console.error('Error creating product:', err);
      alert('ምርት መፍጠር አልተሳካም።');
    }
  };

  const formatCurrency = (amount) => `${(amount || 0).toLocaleString()} ETB`;
  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
    });
  };

  const filteredOrders = statusFilter === 'all' ? orders : orders.filter(o => o.order_status === statusFilter);
  const filteredPayments = paymentFilter === 'all' ? payments :
    payments.filter(p => paymentFilter === 'pending' ? !p.is_verified : p.is_verified);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 animate-spin mx-auto mb-4 text-gray-600" />
          <p className="text-lg font-medium text-gray-700">አድሚን ሰሌዳ በመጫን ላይ...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-8">
      {/* Header */}
      <div className="sticky top-0 z-50 shadow-md bg-gray-900">
        <div className="max-w-7xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button onClick={onLogout} className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors">
                <ArrowLeft className="w-5 h-5 text-white" />
              </button>
              <div>
                <h1 className="text-xl font-bold text-white flex items-center gap-2">
                  <Lock className="w-6 h-6" />
                  አድሚን ሰሌዳ
                </h1>
                <p className="text-gray-400 text-sm">Ethio Shoe Store Admin</p>
              </div>
            </div>
            <button onClick={() => { setRefreshing(true); loadData(); }} disabled={refreshing}
              className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors disabled:opacity-50">
              <RefreshCw className={`w-5 h-5 text-white ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 mt-6">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-600" />
            <p className="text-red-700">{error}</p>
            <button onClick={loadData} className="ml-auto text-red-600 underline">እንደገና ሞክር</button>
          </div>
        )}

        {/* Tabs */}
        <div className="flex gap-2 mb-6 overflow-x-auto">
          {[
            { key: 'orders', label: 'ትዕዛዞች', icon: ShoppingBag },
            { key: 'payments', label: 'ክፍያዎች', icon: CreditCard },
            { key: 'products', label: 'ምርቶች', icon: Package }
          ].map(tab => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                activeTab === tab.key ? 'bg-gray-900 text-white' : 'bg-white text-gray-700 hover:bg-gray-100'
              }`}>
              <tab.icon className="w-5 h-5" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-blue-100"><ShoppingBag className="w-5 h-5 text-blue-600" /></div>
              <div><p className="text-xs text-gray-500">ትዕዛዞች</p><p className="text-xl font-bold">{stats.totalOrders}</p></div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-yellow-100"><AlertCircle className="w-5 h-5 text-yellow-600" /></div>
              <div><p className="text-xs text-gray-500">በመጠባበቅ</p><p className="text-xl font-bold">{stats.pendingOrders}</p></div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-purple-100"><CreditCard className="w-5 h-5 text-purple-600" /></div>
              <div><p className="text-xs text-gray-500">ክፍያ የሚጠብቅ</p><p className="text-xl font-bold">{stats.pendingPayments}</p></div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-green-100"><DollarSign className="w-5 h-5 text-green-600" /></div>
              <div><p className="text-xs text-gray-500">ገቢ</p><p className="text-lg font-bold">{formatCurrency(stats.totalRevenue)}</p></div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-indigo-100"><Package className="w-5 h-5 text-indigo-600" /></div>
              <div><p className="text-xs text-gray-500">ምርቶች</p><p className="text-xl font-bold">{stats.totalProducts}</p></div>
            </div>
          </div>
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-red-100"><AlertTriangle className="w-5 h-5 text-red-600" /></div>
              <div><p className="text-xs text-gray-500">ዝቅተኛ ክምችት</p><p className="text-xl font-bold">{stats.lowStockVariants}</p></div>
            </div>
          </div>
        </div>

        {/* Orders Tab */}
        {activeTab === 'orders' && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
              <h2 className="text-lg font-bold">ትዕዛዞች</h2>
              <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}
                className="text-sm border rounded-lg px-3 py-1.5 bg-white">
                <option value="all">ሁሉም</option>
                {Object.entries(STATUS_CONFIG).map(([key, config]) => (
                  <option key={key} value={key}>{config.labelAm}</option>
                ))}
              </select>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ቁጥር</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ደንበኛ</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ስልክ</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ዋጋ</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ሁኔታ</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ቀን</th>
                    <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ድርጊት</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredOrders.length === 0 ? (
                    <tr><td colSpan="7" className="px-6 py-12 text-center text-gray-500">ምንም ትዕዛዝ የለም</td></tr>
                  ) : filteredOrders.map(order => {
                    const status = STATUS_CONFIG[order.order_status] || STATUS_CONFIG.pending;
                    const StatusIcon = status.icon;
                    return (
                      <tr key={order.id} className="hover:bg-gray-50">
                        <td className="px-6 py-4 font-mono text-sm">#{order.id.slice(0, 8)}</td>
                        <td className="px-6 py-4">{order.customer_name || order.users?.first_name || 'N/A'}</td>
                        <td className="px-6 py-4 text-sm">{order.contact_phone || 'N/A'}</td>
                        <td className="px-6 py-4 font-semibold">{formatCurrency(order.total_amount)}</td>
                        <td className="px-6 py-4">
                          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${status.color}`}>
                            <StatusIcon className="w-3.5 h-3.5" />{status.labelAm}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-500">{formatDate(order.created_at)}</td>
                        <td className="px-6 py-4">
                          <select value={order.order_status} onChange={(e) => handleStatusUpdate(order.id, e.target.value)}
                            className="text-sm border rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500">
                            {Object.entries(STATUS_CONFIG).map(([key, config]) => (
                              <option key={key} value={key}>{config.labelAm}</option>
                            ))}
                          </select>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Payments Tab */}
        {activeTab === 'payments' && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
              <h2 className="text-lg font-bold">ክፍያዎች</h2>
              <select value={paymentFilter} onChange={(e) => setPaymentFilter(e.target.value)}
                className="text-sm border rounded-lg px-3 py-1.5 bg-white">
                <option value="all">ሁሉም</option>
                <option value="pending">ያልተረጋገጠ</option>
                <option value="verified">የተረጋገጠ</option>
              </select>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ትዕዛዝ</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ዘዴ</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">መለያ</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ዋጋ</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ሁኔታ</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ቀን</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ድርጊት</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {filteredPayments.length === 0 ? (
                    <tr><td colSpan="7" className="px-4 py-8 text-center text-gray-500">ምንም ክፍያ የለም</td></tr>
                  ) : filteredPayments.slice(0, 20).map(payment => (
                    <tr key={payment.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono text-sm">#{payment.order_id?.slice(0, 8)}</td>
                      <td className="px-4 py-3 capitalize">{payment.payment_method === 'telebirr' ? 'ቴሌቢር' : 'ሲቢኢ'}</td>
                      <td className="px-4 py-3 font-mono text-sm">{payment.transaction_reference}</td>
                      <td className="px-4 py-3 font-semibold">{formatCurrency(payment.orders?.total_amount || 0)}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          payment.is_verified ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'
                        }`}>{payment.is_verified ? 'የተረጋገጠ' : 'ያልተረጋገጠ'}</span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">{formatDate(payment.created_at)}</td>
                      <td className="px-4 py-3">
                        {!payment.is_verified && (
                          <div className="flex gap-2">
                            <button onClick={() => handlePaymentVerify(payment.id, true)}
                              className="px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700">አረጋግጥ</button>
                            <button onClick={() => handlePaymentVerify(payment.id, false)}
                              className="px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700">ከልክል</button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Products Tab */}
        {activeTab === 'products' && (
          <div>
            <div className="flex justify-end mb-4">
              <button onClick={() => setShowAddProduct(!showAddProduct)}
                className="flex items-center gap-2 px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-gray-800">
                <Plus className="w-5 h-5" />
                አዲስ ምርት አክል
              </button>
            </div>

            {showAddProduct && (
              <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
                <h3 className="text-lg font-bold mb-4">አዲስ ምርት ፍጠር</h3>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium mb-1">ስም *</label>
                    <input type="text" value={newProduct.name} onChange={(e) => setNewProduct({...newProduct, name: e.target.value})}
                      className="w-full px-3 py-2 border rounded-lg" placeholder="ምርት ስም" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">ምድብ *</label>
                    <select value={newProduct.category} onChange={(e) => setNewProduct({...newProduct, category: e.target.value})}
                      className="w-full px-3 py-2 border rounded-lg">
                      <option value="">ምድብ ምረጥ</option>
                      {Object.entries(CATEGORY_LABELS).map(([key, label]) => (
                        <option key={key} value={key}>{label}</option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">ብራንድ</label>
                    <select value={newProduct.brand} onChange={(e) => setNewProduct({...newProduct, brand: e.target.value})}
                      className="w-full px-3 py-2 border rounded-lg">
                      <option value="">ብራንድ ምረጥ</option>
                      {BRANDS.map(b => <option key={b} value={b}>{b}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">ዋጋ (ETB) *</label>
                    <input type="number" value={newProduct.base_price} onChange={(e) => setNewProduct({...newProduct, base_price: e.target.value})}
                      className="w-full px-3 py-2 border rounded-lg" placeholder="0" />
                  </div>
                  <div>
                    <label className="block text-sm font-medium mb-1">መጀመሪያ ዋጋ (ETB)</label>
                    <input type="number" value={newProduct.original_price} onChange={(e) => setNewProduct({...newProduct, original_price: e.target.value})}
                      className="w-full px-3 py-2 border rounded-lg" placeholder="0" />
                  </div>
                  <div className="md:col-span-2">
                    <label className="block text-sm font-medium mb-1">መግለጫ</label>
                    <textarea value={newProduct.description} onChange={(e) => setNewProduct({...newProduct, description: e.target.value})}
                      className="w-full px-3 py-2 border rounded-lg" rows={2} placeholder="ምርት መግለጫ" />
                  </div>
                </div>

                <h4 className="text-md font-semibold mt-6 mb-3">ተለዋዋጮች (Variants)</h4>
                {newProduct.variants.map((variant, index) => (
                  <div key={index} className="grid grid-cols-2 md:grid-cols-5 gap-3 mb-3 p-3 bg-gray-50 rounded-lg">
                    <div>
                      <label className="block text-xs font-medium mb-1">Size</label>
                      <select value={variant.size} onChange={(e) => updateVariant(index, 'size', e.target.value)}
                        className="w-full px-2 py-1.5 border rounded text-sm">
                        {SIZES.map(s => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="block text-xs font-medium mb-1">ቀለም</label>
                      <input type="text" value={variant.color} onChange={(e) => updateVariant(index, 'color', e.target.value)}
                        className="w-full px-2 py-1.5 border rounded text-sm" placeholder="ጥቁር" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium mb-1">ክምችት</label>
                      <input type="number" value={variant.stock} onChange={(e) => updateVariant(index, 'stock', e.target.value)}
                        className="w-full px-2 py-1.5 border rounded text-sm" min="0" />
                    </div>
                    <div>
                      <label className="block text-xs font-medium mb-1">ምስል</label>
                      <div className="flex items-center gap-2">
                        <input type="file" accept="image/*" onChange={(e) => handleImageUpload(e, index)}
                          className="hidden" id={`image-${index}`} />
                        <label htmlFor={`image-${index}`} className="flex items-center gap-1 px-2 py-1.5 bg-gray-200 rounded cursor-pointer hover:bg-gray-300 text-sm">
                          <Camera className="w-4 h-4" />
                          {uploadingImage ? 'በመስቀል...' : 'ምስል'}
                        </label>
                        {variant.image_url && <span className="text-xs text-green-600">✓</span>}
                      </div>
                    </div>
                    <div className="flex items-end">
                      <button onClick={() => removeVariant(index)} disabled={newProduct.variants.length === 1}
                        className="p-1.5 text-red-600 hover:bg-red-50 rounded disabled:opacity-30">
                        <X className="w-5 h-5" />
                      </button>
                    </div>
                  </div>
                ))}
                <button onClick={addVariant} className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 mb-4">
                  <Plus className="w-4 h-4" /> ተጨማሪ ተለዋዋጭ አክል
                </button>

                <div className="flex gap-3">
                  <button onClick={handleCreateProduct}
                    className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
                    <Save className="w-5 h-5" /> አስቀምጥ
                  </button>
                  <button onClick={() => setShowAddProduct(false)}
                    className="px-4 py-2 border rounded-lg hover:bg-gray-50">ሰርዝ</button>
                </div>
              </div>
            )}

            {/* Products List */}
            <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ስም</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ምድብ</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ዋጋ</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ተለዋዋጮች</th>
                      <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">ዝቅተኛ ክምችት</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {products.map(product => {
                      const lowStock = (product.product_variants || []).filter(v => (v.stock || 0) < 5);
                      return (
                        <tr key={product.id} className="hover:bg-gray-50">
                          <td className="px-6 py-4 font-medium">{product.name}</td>
                          <td className="px-6 py-4">{CATEGORY_LABELS[product.category] || product.category}</td>
                          <td className="px-6 py-4">{formatCurrency(product.base_price)}</td>
                          <td className="px-6 py-4">{(product.product_variants || []).length}</td>
                          <td className="px-6 py-4">
                            {lowStock.length > 0 && (
                              <span className="inline-flex items-center gap-1 text-red-600 text-sm">
                                <AlertTriangle className="w-4 h-4" />{lowStock.length}
                              </span>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Admin Login Gate
function AdminGate({ children }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [accessCode, setAccessCode] = useState('');
  const [error, setError] = useState('');
  const [showDashboard, setShowDashboard] = useState(false);

  useEffect(() => {
    const savedAuth = localStorage.getItem('adminAuth');
    if (savedAuth === 'true') {
      setIsAuthenticated(true);
      setShowDashboard(true);
    }
  }, []);

  const handleLogin = (e) => {
    e.preventDefault();
    if (accessCode === ADMIN_ACCESS_CODE) {
      setIsAuthenticated(true);
      setShowDashboard(true);
      localStorage.setItem('adminAuth', 'true');
      setError('');
    } else {
      setError('የማስገቢያ ኮድ ልክ አይደለም');
      setAccessCode('');
    }
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setShowDashboard(false);
    localStorage.removeItem('adminAuth');
  };

  if (showDashboard && isAuthenticated) {
    return <AdminDashboard onLogout={handleLogout} />;
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4 bg-gray-50">
      <div className="max-w-md w-full">
        <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-200">
          <div className="text-center mb-8">
            <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4 bg-gray-900">
              <Lock className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold mb-2">አድሚን መግቢያ</h1>
            <p className="text-sm text-gray-500">የእርስዎን የመግቢያ ኮድ ያስገቡ</p>
          </div>
          <form onSubmit={handleLogin} className="space-y-4">
            <input type="password" value={accessCode} onChange={(e) => setAccessCode(e.target.value)}
              placeholder="የመግቢያ ኮድ" className="w-full px-4 py-3 rounded-xl border-2 border-gray-200 focus:outline-none focus:border-blue-500" autoFocus />
            {error && <div className="text-red-500 text-sm text-center">{error}</div>}
            <button type="submit" className="w-full py-3 rounded-xl font-bold text-lg bg-gray-900 text-white hover:bg-gray-800">
              <div className="flex items-center justify-center gap-2"><Unlock className="w-5 h-5" />ግባ</div>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default AdminGate;
