import React, { useState, useEffect } from 'react';
import { db } from './supabaseClient';
import {
  ShoppingBag,
  Package,
  Users,
  CreditCard,
  TrendingUp,
  AlertCircle,
  CheckCircle,
  Truck,
  XCircle,
  Plus,
  Edit,
  Trash2,
  Eye
} from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [products, setProducts] = useState([]);
  const [orders, setOrders] = useState([]);
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalProducts: 0,
    totalOrders: 0,
    pendingOrders: 0,
    totalRevenue: 0
  });

  useEffect(() => {
    loadDashboardData();
  }, []);

  async function loadDashboardData() {
    try {
      setLoading(true);
      const [productsData, ordersData, paymentsData] = await Promise.all([
        db.getProducts(),
        db.getOrders(),
        db.getPayments()
      ]);

      setProducts(productsData || []);
      setOrders(ordersData || []);
      setPayments(paymentsData || []);

      // Calculate stats
      const totalRevenue = (ordersData || [])
        .filter(o => o.order_status === 'delivered')
        .reduce((sum, o) => sum + (o.total_amount || 0), 0);

      setStats({
        totalProducts: productsData?.length || 0,
        totalOrders: ordersData?.length || 0,
        pendingOrders: (ordersData || []).filter(o => o.order_status === 'pending').length,
        totalRevenue
      });
    } catch (error) {
      console.error('Error loading data:', error);
    } finally {
      setLoading(false);
    }
  }

  const handleUpdateOrderStatus = async (orderId, newStatus) => {
    try {
      await db.updateOrderStatus(orderId, newStatus);
      await loadDashboardData();
    } catch (error) {
      console.error('Error updating order:', error);
    }
  };

  const handleVerifyPayment = async (paymentId) => {
    try {
      await db.verifyPayment(paymentId, 7098279917);
      await loadDashboardData();
    } catch (error) {
      console.error('Error verifying payment:', error);
    }
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      pending: { class: 'status-pending', icon: AlertCircle, text: '⏱️ Pending' },
      confirmed: { class: 'status-confirmed', icon: CheckCircle, text: '✅ Confirmed' },
      shipped: { class: 'status-shipped', icon: Truck, text: '🚚 Shipped' },
      delivered: { class: 'status-delivered', icon: CheckCircle, text: '📦 Delivered' },
      cancelled: { class: 'status-cancelled', icon: XCircle, text: '❌ Cancelled' }
    };
    return statusConfig[status] || statusConfig.pending;
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-gray-700 font-semibold">Loading Dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-gray-900 text-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <ShoppingBag className="h-10 w-10" />
              <div>
                <h1 className="text-3xl font-bold">Ethio Shoe Store</h1>
                <p className="text-gray-300">Admin Dashboard (አድሚን ማዘዣ ሰሌዳ)</p>
              </div>
            </div>
            <div className="flex items-center space-x-2">
              <span className="px-3 py-1 bg-gray-800 rounded-full text-sm font-medium">
                BOT_TOKEN: 8651460654:AAG9S_BOfqvf0QhUupDCiMrXVc4yLdOj3Uw
              </span>
            </div>
          </div>

          {/* Navigation Tabs */}
          <nav className="mt-6 flex space-x-4">
            {[
              { id: 'dashboard', label: 'Dashboard', icon: TrendingUp },
              { id: 'products', label: 'Products (ምርቶች)', icon: Package },
              { id: 'orders', label: 'Orders (ትዕዛዞች)', icon: ShoppingBag },
              { id: 'payments', label: 'Payments (ክፍያዎች)', icon: CreditCard }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 px-6 py-3 rounded-lg font-semibold transition-all ${
                  activeTab === tab.id
                    ? 'bg-white text-gray-900'
                    : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                }`}
              >
                <tab.icon className="h-5 w-5" />
                <span>{tab.label}</span>
              </button>
            ))}
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {/* Dashboard Tab */}
        {activeTab === 'dashboard' && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Dashboard Overview</h2>

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
              <div className="card">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Total Products</p>
                    <p className="text-3xl font-bold text-gray-900">{stats.totalProducts}</p>
                  </div>
                  <Package className="h-12 w-12 text-gray-400" />
                </div>
              </div>

              <div className="card">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Total Orders</p>
                    <p className="text-3xl font-bold text-gray-900">{stats.totalOrders}</p>
                  </div>
                  <ShoppingBag className="h-12 w-12 text-gray-400" />
                </div>
              </div>

              <div className="card">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Pending Orders</p>
                    <p className="text-3xl font-bold text-yellow-600">{stats.pendingOrders}</p>
                  </div>
                  <AlertCircle className="h-12 w-12 text-yellow-400" />
                </div>
              </div>

              <div className="card">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Total Revenue</p>
                    <p className="text-3xl font-bold text-green-600">{stats.totalRevenue}</p>
                    <p className="text-sm text-gray-500">ETB (ብር)</p>
                  </div>
                  <TrendingUp className="h-12 w-12 text-green-400" />
                </div>
              </div>
            </div>

            {/* Recent Orders */}
            <div className="card">
              <h3 className="text-xl font-bold text-gray-900 mb-4">Recent Orders (ትዕዛዞች)</h3>
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead>
                    <tr className="border-b-2 border-gray-200">
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Order ID</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Customer</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Phone</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Amount (ETB)</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.slice(0, 5).map((order) => {
                      const statusBadge = getStatusBadge(order.order_status);
                      return (
                        <tr key={order.id} className="border-b border-gray-200">
                          <td className="px-4 py-3 text-sm font-mono text-gray-700">#{order.id.slice(0, 8)}</td>
                          <td className="px-4 py-3 text-sm text-gray-900">{order.users?.first_name || 'N/A'}</td>
                          <td className="px-4 py-3 text-sm text-gray-700">{order.contact_phone}</td>
                          <td className="px-4 py-3 text-sm font-semibold text-gray-900">{order.total_amount} ETB (ብር)</td>
                          <td className="px-4 py-3">
                            <span className={`px-3 py-1 rounded-full text-xs font-semibold ${statusBadge.class}`}>
                              {statusBadge.text}
                            </span>
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

        {/* Products Tab */}
        {activeTab === 'products' && (
          <div>
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-gray-900">Products (ምርቶች)</h2>
              <button className="btn-primary flex items-center space-x-2">
                <Plus className="h-5 w-5" />
                <span>Add Product</span>
              </button>
            </div>

            <div className="product-grid">
              {products.map((product) => (
                <div key={product.id} className="card">
                  {product.product_variants && product.product_variants[0]?.image_url && (
                    <img
                      src={product.product_variants[0].image_url}
                      alt={product.name}
                      className="w-full h-48 object-cover rounded-lg mb-4"
                    />
                  )}
                  <h3 className="text-lg font-bold text-gray-900">{product.name}</h3>
                  <p className="text-sm text-gray-600 mb-2">{product.description || 'No description'}</p>
                  <p className="text-sm text-gray-700 mb-2">
                    <span className="font-semibold">Category:</span> {product.category}
                  </p>
                  <div className="mb-2">
                    {product.original_price && product.original_price > product.base_price ? (
                      <div>
                        <span className="line-through text-gray-500 mr-2">{product.original_price}</span>
                        <span className="etb-price text-xl">{product.base_price}</span>
                      </div>
                    ) : (
                      <span className="etb-price text-xl">{product.base_price}</span>
                    )}
                  </div>

                  {/* Variants */}
                  {product.product_variants && product.product_variants.length > 0 && (
                    <div className="mt-4 border-t pt-4">
                      <p className="text-sm font-semibold text-gray-700 mb-2">Variants:</p>
                      <div className="space-y-2">
                        {product.product_variants.map((variant) => (
                          <div key={variant.id} className="flex items-center justify-between text-sm">
                            <span className="text-gray-700">
                              Size: {variant.size} | Color: {variant.color}
                            </span>
                            <span className={`font-semibold ${variant.stock > 0 ? 'text-green-600' : 'text-red-600'}`}>
                              Stock: {variant.stock}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <div className="mt-4 flex space-x-2">
                    <button className="btn-accent text-sm flex-1">
                      <Edit className="h-4 w-4 inline mr-1" />
                      Edit
                    </button>
                    <button className="bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-lg text-sm flex-1">
                      <Trash2 className="h-4 w-4 inline mr-1" />
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Orders Tab */}
        {activeTab === 'orders' && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Orders Management (የትዕዛዞች አስተዳደር)</h2>

            <div className="card">
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead>
                    <tr className="border-b-2 border-gray-200">
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Order ID</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Customer</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Phone</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Subtotal (ETB)</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Delivery (ETB)</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Total (ETB)</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Status</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.map((order) => {
                      const statusBadge = getStatusBadge(order.order_status);
                      return (
                        <tr key={order.id} className="border-b border-gray-200 hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-mono text-gray-700">#{order.id.slice(0, 8)}</td>
                          <td className="px-4 py-3 text-sm text-gray-900">{order.users?.first_name || 'N/A'}</td>
                          <td className="px-4 py-3 text-sm text-gray-700">{order.contact_phone}</td>
                          <td className="px-4 py-3 text-sm text-gray-900">{order.subtotal} ETB</td>
                          <td className="px-4 py-3 text-sm text-gray-900">{order.delivery_fee} ETB</td>
                          <td className="px-4 py-3 text-sm font-bold text-gray-900">{order.total_amount} ETB (ብር)</td>
                          <td className="px-4 py-3">
                            <span className={`px-3 py-1 rounded-full text-xs font-semibold inline-block ${statusBadge.class}`}>
                              {statusBadge.text}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <select
                              value={order.order_status}
                              onChange={(e) => handleUpdateOrderStatus(order.id, e.target.value)}
                              className="px-3 py-1 border border-gray-300 rounded-lg text-sm font-semibold focus:ring-2 focus:ring-blue-500"
                            >
                              <option value="pending">⏱️ Pending</option>
                              <option value="confirmed">✅ Confirmed</option>
                              <option value="shipped">🚚 Shipped</option>
                              <option value="delivered">📦 Delivered</option>
                              <option value="cancelled">❌ Cancelled</option>
                            </select>
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

        {/* Payments Tab */}
        {activeTab === 'payments' && (
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Payment Verification (የክፍያ ማረጋገጫ)</h2>

            <div className="card">
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead>
                    <tr className="border-b-2 border-gray-200">
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Payment ID</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Order ID</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Method</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Reference</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Status</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-gray-900">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {payments.map((payment) => (
                      <tr key={payment.id} className="border-b border-gray-200 hover:bg-gray-50">
                        <td className="px-4 py-3 text-sm font-mono text-gray-700">#{payment.id.slice(0, 8)}</td>
                        <td className="px-4 py-3 text-sm font-mono text-gray-700">
                          #{payment.order_id?.slice(0, 8) || 'N/A'}
                        </td>
                        <td className="px-4 py-3">
                          <span className={`px-3 py-1 rounded-lg text-xs font-semibold ${
                            payment.payment_method === 'telebirr'
                              ? 'bg-yellow-100 text-yellow-800'
                              : 'bg-orange-100 text-orange-800'
                          }`}>
                            {payment.payment_method === 'telebirr' ? '📱 Telebirr' : '🏦 CBE'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm font-mono text-gray-900">{payment.transaction_reference}</td>
                        <td className="px-4 py-3">
                          <span className={`px-3 py-1 rounded-full text-xs font-semibold inline-block ${
                            payment.is_verified ? 'status-delivered' : 'status-pending'
                          }`}>
                            {payment.is_verified ? '✅ Verified' : '⏱️ Pending'}
                          </span>
                        </td>
                        <td className="px-4 py-3">
                          {!payment.is_verified && (
                            <button
                              onClick={() => handleVerifyPayment(payment.id)}
                              className="btn-success text-sm"
                            >
                              <CheckCircle className="h-4 w-4 inline mr-1" />
                              Verify
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="bg-gray-900 text-white py-6 mt-12">
        <div className="max-w-7xl mx-auto px-4 text-center">
          <p className="text-gray-400">
            © 2024 Ethio Shoe Store - Premium Ethiopian Footwear | Developed with ❤️
          </p>
          <p className="text-gray-500 text-sm mt-2">
            All prices in Ethiopian Birr (ETB/ብር)
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
