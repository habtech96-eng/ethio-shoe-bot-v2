import React, { useState, useEffect } from 'react';
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
  Activity
} from 'lucide-react';

// Admin password (in production, this should be a proper auth system)
const ADMIN_ACCESS_CODE = 'ETHIO_ADMIN_2026';

const STATUS_CONFIG = {
  pending: {
    label: '⏱️ Pending',
    labelAm: 'በመጠባበቅ ላይ',
    color: 'bg-gray-100 text-gray-800 border-gray-300',
    icon: AlertCircle
  },
  confirmed: {
    label: '✅ Confirmed',
    labelAm: 'የተረጋገጠ',
    color: 'bg-blue-100 text-blue-800 border-blue-300',
    icon: CheckCircle
  },
  processing: {
    label: '⚙️ Processing',
    labelAm: 'በሂደት ላይ',
    color: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    icon: RefreshCw
  },
  shipped: {
    label: '🚚 Shipped',
    labelAm: 'ተልኳል',
    color: 'bg-purple-100 text-purple-800 border-purple-300',
    icon: Truck
  },
  delivered: {
    label: '📦 Delivered',
    labelAm: 'ተልኳል',
    color: 'bg-green-100 text-green-800 border-green-300',
    icon: CheckCircle
  },
  cancelled: {
    label: '❌ Cancelled',
    labelAm: 'ተሰርዟል',
    color: 'bg-red-100 text-red-800 border-red-300',
    icon: XCircle
  }
};

function AdminDashboard({ onLogout }) {
  const [orders, setOrders] = useState([]);
  const [products, setProducts] = useState([]);
  const [stats, setStats] = useState({
    totalOrders: 0,
    pendingOrders: 0,
    totalRevenue: 0,
    totalProducts: 0
  });
  const [loading, setLoading] = useState(true);
  const [selectedOrder, setSelectedOrder] = useState(null);
  const [updatingStatus, setUpdatingStatus] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);

      // Fetch orders
      const { data: ordersData, error: ordersError } = await supabase
        .from('orders')
        .select('*')
        .order('created_at', { ascending: false });

      if (ordersError) throw ordersError;

      // Fetch products
      const { data: productsData, error: productsError } = await supabase
        .from('products')
        .select('id, name, base_price, is_active')
        .eq('is_active', true);

      if (productsError) throw productsError;

      setOrders(ordersData || []);
      setProducts(productsData || []);

      // Calculate stats
      const totalRevenue = (ordersData || [])
        .filter(o => o.order_status === 'delivered')
        .reduce((sum, o) => sum + (o.total_amount || 0), 0);

      setStats({
        totalOrders: ordersData?.length || 0,
        pendingOrders: (ordersData || []).filter(o => o.order_status === 'pending').length,
        totalRevenue,
        totalProducts: productsData?.length || 0
      });

    } catch (error) {
      console.error('Error loading dashboard data:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleStatusUpdate = async (orderId, newStatus) => {
    try {
      setUpdatingStatus(orderId);

      const { error } = await supabase
        .from('orders')
        .update({
          order_status: newStatus,
          updated_at: new Date().toISOString()
        })
        .eq('id', orderId);

      if (error) throw error;

      // Update local state
      setOrders(prev =>
        prev.map(order =>
          order.id === orderId
            ? { ...order, order_status: newStatus }
            : order
        )
      );

      // Update stats
      loadData();

    } catch (error) {
      console.error('Error updating order status:', error);
      alert('Failed to update order status');
    } finally {
      setUpdatingStatus(null);
    }
  };

  const formatCurrency = (amount) => {
    return `${(amount || 0).toLocaleString()} ETB`;
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ backgroundColor: 'var(--tg-theme-bg-color, #f7fafc)' }}>
        <div className="text-center">
          <RefreshCw className="w-12 h-12 animate-spin mx-auto mb-4" style={{ color: 'var(--tg-theme-button-color, #1a202c)' }} />
          <p className="text-lg font-medium" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
            Loading Admin Dashboard...
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen pb-8" style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }}>
      {/* Header */}
      <div className="sticky top-0 z-50 shadow-md" style={{ backgroundColor: 'var(--tg-theme-button-color, #1a202c)' }}>
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <button
                onClick={onLogout}
                className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors"
                title="Logout"
              >
                <ArrowLeft className="w-6 h-6 text-white" />
              </button>
              <div>
                <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                  <Lock className="w-7 h-7" />
                  Admin Dashboard
                </h1>
                <p className="text-gray-300 text-sm">አድሚን ማዘዣ ሰሌዳ</p>
              </div>
            </div>
            <button
              onClick={() => {
                setRefreshing(true);
                loadData();
              }}
              disabled={refreshing}
              className="p-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors disabled:opacity-50"
              title="Refresh Data"
            >
              <RefreshCw className={`w-6 h-6 text-white ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 mt-8">
        {/* Stats Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-lg bg-blue-100">
                <ShoppingBag className="w-6 h-6 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Total Orders</p>
                <p className="text-2xl font-bold text-gray-900">{stats.totalOrders}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-lg bg-yellow-100">
                <AlertCircle className="w-6 h-6 text-yellow-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Pending</p>
                <p className="text-2xl font-bold text-gray-900">{stats.pendingOrders}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-lg bg-green-100">
                <TrendingUp className="w-6 h-6 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Revenue</p>
                <p className="text-2xl font-bold text-gray-900">{formatCurrency(stats.totalRevenue)}</p>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-lg bg-purple-100">
                <Package className="w-6 h-6 text-purple-600" />
              </div>
              <div>
                <p className="text-sm text-gray-600">Products</p>
                <p className="text-2xl font-bold text-gray-900">{stats.totalProducts}</p>
              </div>
            </div>
          </div>
        </div>

        {/* Orders Table */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200" style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }}>
            <h2 className="text-lg font-bold" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
              Recent Orders (ትዕዛዞች)
            </h2>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200" style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }}>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                    Order ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                    Customer
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                    Amount
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                    Date
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-semibold uppercase tracking-wider" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {orders.length === 0 ? (
                  <tr>
                    <td colSpan="6" className="px-6 py-12 text-center">
                      <Package className="w-12 h-12 mx-auto mb-3 opacity-20" style={{ color: 'var(--tg-theme-hint-color, #6b7280)' }} />
                      <p style={{ color: 'var(--tg-theme-hint-color, #6b7280)' }}>No orders yet</p>
                    </td>
                  </tr>
                ) : (
                  orders.map((order) => {
                    const status = STATUS_CONFIG[order.order_status] || STATUS_CONFIG.pending;
                    const StatusIcon = status.icon;

                    return (
                      <tr key={order.id} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="font-mono text-sm" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                            #{order.id.slice(0, 8)}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div>
                            <p className="font-medium" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                              {order.customer_name || 'N/A'}
                            </p>
                            <p className="text-sm" style={{ color: 'var(--tg-theme-hint-color, #6b7280)' }}>
                              {order.customer_phone || 'N/A'}
                            </p>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="font-semibold" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                            {formatCurrency(order.total_amount)}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium border ${status.color}`}>
                            <StatusIcon className="w-4 h-4" />
                            {status.label}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm" style={{ color: 'var(--tg-theme-hint-color, #6b7280)' }}>
                          {formatDate(order.created_at)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <select
                            value={order.order_status}
                            onChange={(e) => handleStatusUpdate(order.id, e.target.value)}
                            disabled={updatingStatus === order.id}
                            className="text-sm border rounded-lg px-3 py-2 focus:outline-none focus:ring-2"
                            style={{
                              backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)',
                              color: 'var(--tg-theme-text-color, #1a202c)'
                            }}
                          >
                            {Object.entries(STATUS_CONFIG).map(([key, config]) => (
                              <option key={key} value={key}>
                                {config.label}
                              </option>
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
    <div className="min-h-screen flex items-center justify-center px-4" style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }}>
      <div className="max-w-md w-full">
        <div className="bg-white rounded-2xl shadow-xl p-8 border border-gray-200">
          <div className="text-center mb-8">
            <div className="w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4" style={{ backgroundColor: 'var(--tg-theme-button-color, #1a202c)' }}>
              <Lock className="w-8 h-8 text-white" />
            </div>
            <h1 className="text-2xl font-bold mb-2" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
              Admin Access
            </h1>
            <p className="text-sm" style={{ color: 'var(--tg-theme-hint-color, #6b7280)' }}>
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
                className="w-full px-4 py-3 rounded-xl border-2 focus:outline-none focus:border-blue-500 transition-colors"
                style={{
                  backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)',
                  color: 'var(--tg-theme-text-color, #1a202c)'
                }}
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
              className="w-full py-3 rounded-xl font-bold text-lg transition-all hover:scale-105"
              style={{
                backgroundColor: 'var(--tg-theme-button-color, #1a202c)',
                color: 'var(--tg-theme-button-text-color, #ffffff)'
              }}
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
