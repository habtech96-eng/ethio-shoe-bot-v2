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
  Users,
  CreditCard,
  ArrowLeft,
  RefreshCw,
  Eye,
  Edit3,
  Send,
  Lock,
  Unlock,
  Activity,
  AlertTriangle,
  DollarSign
} from 'lucide-react';

// Admin password (in production, this should come from env or proper auth)
const ADMIN_ACCESS_CODE = 'ETHIO_ADMIN_2026';

const STATUS_CONFIG = {
  pending: {
    label: 'Pending',
    labelAm: 'በመጠባበቅ ላይ',
    color: 'bg-amber-100 text-amber-800 border-amber-300',
    icon: AlertCircle
  },
  confirmed: {
    label: 'Confirmed',
    labelAm: 'የተረጋገጠ',
    color: 'bg-blue-100 text-blue-800 border-blue-300',
    icon: CheckCircle
  },
  shipped: {
    label: 'Shipped',
    labelAm: 'ተልኳል',
    color: 'bg-purple-100 text-purple-800 border-purple-300',
    icon: Truck
  },
  delivered: {
    label: 'Delivered',
    labelAm: 'ተልኳል',
    color: 'bg-green-100 text-green-800 border-green-300',
    icon: Package
  },
  cancelled: {
    label: 'Cancelled',
    labelAm: 'ተሰርዟል',
    color: 'bg-red-100 text-red-800 border-red-300',
    icon: XCircle
  }
};

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

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Fetch orders with user info and items
      const { data: ordersData, error: ordersError } = await supabase
        .from('orders')
        .select('*, users(first_name, telegram_id), order_items(*), payments(*)')
        .order('created_at', { ascending: false });

      if (ordersError) throw ordersError;

      // Fetch products with variants for stock monitoring
      const { data: productsData, error: productsError } = await supabase
        .from('products')
        .select('id, name, base_price, is_active, product_variants(id, stock, size, color)')
        .eq('is_active', true);

      if (productsError) throw productsError;

      // Fetch all payments
      const { data: paymentsData, error: paymentsError } = await supabase
        .from('payments')
        .select('*, orders(total_amount)')
        .order('created_at', { ascending: false });

      if (paymentsError) throw paymentsError;

      setOrders(ordersData || []);
      setProducts(productsData || []);
      setPayments(paymentsData || []);

      // Calculate stats
      const totalRevenue = (ordersData || [])
        .filter(o => o.order_status === 'delivered')
        .reduce((sum, o) => sum + (o.total_amount || 0), 0);

      const pendingPayments = (paymentsData || [])
        .filter(p => p.is_verified === false)
        .length;

      // Count low stock variants (stock < 5)
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
      setError('Failed to load data. Please check your connection and try again.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadData();
  }, [loadData]);

  // Real-time subscription for orders
  useEffect(() => {
    const channel = supabase
      .channel('admin-dashboard-orders')
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'orders' },
        () => {
          // Reload data on any order change
          loadData();
        }
      )
      .on(
        'postgres_changes',
        { event: '*', schema: 'public', table: 'payments' },
        () => {
          loadData();
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, [loadData]);

  const handleStatusUpdate = async (orderId, newStatus) => {
    try {
      const { error } = await supabase
        .from('orders')
        .update({
          order_status: newStatus,
          updated_at: new Date().toISOString()
        })
        .eq('id', orderId);

      if (error) throw error;

      // Update local state immediately for responsive UI
      setOrders(prev =>
        prev.map(order =>
          order.id === orderId
            ? { ...order, order_status: newStatus }
            : order
        )
      );

    } catch (err) {
      console.error('Error updating order status:', err);
      alert('Failed to update order status. Please try again.');
    }
  };

  const handlePaymentVerify = async (paymentId, verify) => {
    try {
      const update = verify
        ? { is_verified: true, verified_at: new Date().toISOString() }
        : { is_verified: false };

      const { error } = await supabase
        .from('payments')
        .update(update)
        .eq('id', paymentId);

      if (error) throw error;

      // If rejecting, also cancel the order
      if (!verify) {
        const payment = payments.find(p => p.id === paymentId);
        if (payment?.order_id) {
          await supabase
            .from('orders')
            .update({ order_status: 'cancelled' })
            .eq('id', payment.order_id);
        }
      } else {
        // If verifying, confirm the order
        const payment = payments.find(p => p.id === paymentId);
        if (payment?.order_id) {
          await supabase
            .from('orders')
            .update({ order_status: 'confirmed' })
            .eq('id', payment.order_id);
        }
      }

      loadData();
    } catch (err) {
      console.error('Error updating payment:', err);
      alert('Failed to update payment status.');
    }
  };

  const formatCurrency = (amount) => {
    return `${(amount || 0).toLocaleString()} ETB`;
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'N/A';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Filter orders by status
  const filteredOrders = statusFilter === 'all'
    ? orders
    : orders.filter(o => o.order_status === statusFilter);

  // Filter payments
  const filteredPayments = paymentFilter === 'all'
    ? payments
    : payments.filter(p =>
        paymentFilter === 'pending' ? !p.is_verified : p.is_verified
      );

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          <RefreshCw className="w-12 h-12 animate-spin mx-auto mb-4 text-gray-600" />
          <p className="text-lg font-medium text-gray-700">
            Loading Admin Dashboard...
          </p>
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
              <button
                onClick={onLogout}
                className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors"
                title="Logout"
              >
                <ArrowLeft className="w-5 h-5 text-white" />
              </button>
              <div>
                <h1 className="text-xl font-bold text-white flex items-center gap-2">
                  <Lock className="w-6 h-6" />
                  Admin Dashboard
                </h1>
                <p className="text-gray-400 text-sm">አድሚን ማዘዣ ሰሌዳ</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => { setRefreshing(true); loadData(); }}
                disabled={refreshing}
                className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors disabled:opacity-50"
                title="Refresh Data"
              >
                <RefreshCw className={`w-5 h-5 text-white ${refreshing ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 mt-6">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-red-600" />
            <p className="text-red-700">{error}</p>
            <button onClick={loadData} className="ml-auto text-red-600 underline">
              Retry
            </button>
          </div>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-blue-100">
                <ShoppingBag className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-xs text-gray-500">Orders</p>
                <p className="text-xl font-bold text-gray-900">{stats.totalOrders}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-amber-100">
                <AlertCircle className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <p className="text-xs text-gray-500">Pending</p>
                <p className="text-xl font-bold text-gray-900">{stats.pendingOrders}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-purple-100">
                <CreditCard className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-xs text-gray-500">Payments</p>
                <p className="text-xl font-bold text-gray-900">{stats.pendingPayments}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-green-100">
                <DollarSign className="w-5 h-5 text-green-600" />
              </div>
              <div>
                <p className="text-xs text-gray-500">Revenue</p>
                <p className="text-lg font-bold text-gray-900">{formatCurrency(stats.totalRevenue)}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-indigo-100">
                <Package className="w-5 h-5 text-indigo-600" />
              </div>
              <div>
                <p className="text-xs text-gray-500">Products</p>
                <p className="text-xl font-bold text-gray-900">{stats.totalProducts}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-lg bg-red-100">
                <AlertTriangle className="w-5 h-5 text-red-600" />
              </div>
              <div>
                <p className="text-xs text-gray-500">Low Stock</p>
                <p className="text-xl font-bold text-gray-900">{stats.lowStockVariants}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Payments Section */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden mb-8">
          <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900">
              Payments (ክፍያዎች)
            </h2>
            <select
              value={paymentFilter}
              onChange={(e) => setPaymentFilter(e.target.value)}
              className="text-sm border rounded-lg px-3 py-1.5 bg-white"
            >
              <option value="all">All</option>
              <option value="pending">Pending</option>
              <option value="verified">Verified</option>
            </select>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Order</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Method</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Reference</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Amount</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Status</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Date</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredPayments.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="px-4 py-8 text-center text-gray-500">
                      No payments found
                    </td>
                  </tr>
                ) : (
                  filteredPayments.slice(0, 10).map((payment) => (
                    <tr key={payment.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3 font-mono text-sm">
                        #{payment.order_id?.slice(0, 8) || 'N/A'}
                      </td>
                      <td className="px-4 py-3">
                        <span className="capitalize">{payment.payment_method}</span>
                      </td>
                      <td className="px-4 py-3 font-mono text-sm">
                        {payment.transaction_reference || 'N/A'}
                      </td>
                      <td className="px-4 py-3 font-semibold">
                        {formatCurrency(payment.orders?.total_amount || 0)}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          payment.is_verified
                            ? 'bg-green-100 text-green-700'
                            : 'bg-amber-100 text-amber-700'
                        }`}>
                          {payment.is_verified ? 'Verified' : 'Pending'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {formatDate(payment.created_at)}
                      </td>
                      <td className="px-4 py-3">
                        {!payment.is_verified && (
                          <div className="flex gap-2">
                            <button
                              onClick={() => handlePaymentVerify(payment.id, true)}
                              className="px-3 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700"
                            >
                              Verify
                            </button>
                            <button
                              onClick={() => handlePaymentVerify(payment.id, false)}
                              className="px-3 py-1 bg-red-600 text-white text-xs rounded hover:bg-red-700"
                            >
                              Reject
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Orders Section */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex items-center justify-between">
            <h2 className="text-lg font-bold text-gray-900">
              Recent Orders (ትዕዛዞች)
            </h2>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="text-sm border rounded-lg px-3 py-1.5 bg-white"
            >
              <option value="all">All Statuses</option>
              {Object.entries(STATUS_CONFIG).map(([key, config]) => (
                <option key={key} value={key}>{config.label}</option>
              ))}
            </select>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Order ID</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Customer</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Phone</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Amount</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Date</th>
                  <th className="px-6 py-3 text-left text-xs font-semibold text-gray-600 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredOrders.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="px-6 py-12 text-center">
                      <Package className="w-10 h-10 mx-auto mb-2 opacity-20 text-gray-400" />
                      <p className="text-gray-500">No orders found</p>
                    </td>
                  </tr>
                ) : (
                  filteredOrders.map((order) => {
                    const status = STATUS_CONFIG[order.order_status] || STATUS_CONFIG.pending;
                    const StatusIcon = status.icon;
                    const userData = order.users || {};

                    return (
                      <tr key={order.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="font-mono text-sm">#{order.id.slice(0, 8)}</span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <p className="font-medium">
                            {order.customer_name || userData.first_name || 'N/A'}
                          </p>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm">
                          {order.contact_phone || 'N/A'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="font-semibold">{formatCurrency(order.total_amount)}</span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${status.color}`}>
                            <StatusIcon className="w-3.5 h-3.5" />
                            {status.label}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                          {formatDate(order.created_at)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <select
                            value={order.order_status}
                            onChange={(e) => handleStatusUpdate(order.id, e.target.value)}
                            className="text-sm border rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                          >
                            {Object.entries(STATUS_CONFIG).map(([key, config]) => (
                              <option key={key} value={key}>{config.label}</option>
                            ))}
                          </select>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>
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

  // Check localStorage for saved auth
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
      setError('Invalid access code');
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
            <h1 className="text-2xl font-bold mb-2 text-gray-900">
              Admin Access
            </h1>
            <p className="text-sm text-gray-500">
              Enter your access code to continue
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <input
                type="password"
                value={accessCode}
                onChange={(e) => setAccessCode(e.target.value)}
                placeholder="Access Code"
                className="w-full px-4 py-3 rounded-xl border-2 border-gray-200 focus:outline-none focus:border-blue-500 transition-colors"
                autoFocus
              />
            </div>

            {error && (
              <div className="text-red-500 text-sm text-center">
                {error}
              </div>
            )}

            <button
              type="submit"
              className="w-full py-3 rounded-xl font-bold text-lg transition-all hover:scale-[1.02] bg-gray-900 text-white"
            >
              <div className="flex items-center justify-center gap-2">
                <Unlock className="w-5 h-5" />
                Access Dashboard
              </div>
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

export default AdminGate;
