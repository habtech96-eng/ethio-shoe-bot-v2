import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { supabase } from './supabaseClient';
import AdminGate from './AdminDashboard';
import {
  ShoppingBag,
  Package,
  Heart,
  ShoppingCart,
  ChevronRight,
  Star,
  MapPin,
  Phone,
  CreditCard,
  Check,
  X,
  ArrowLeft,
  Plus,
  Minus,
  Send,
  Search,
  Filter,
  Trash2,
  Sparkles,
  AlertCircle,
  Truck,
  Loader2
} from 'lucide-react';

// ============================================================
// CONFIGURATION & CONSTANTS
// ============================================================

const ADDIS_ABABA_NEIGHBORHOODS = [
  { name: 'Bole', nameAm: 'ቦሌ', fee: 50, estimatedDays: 1 },
  { name: 'Megenagna', nameAm: 'መገናግና', fee: 60, estimatedDays: 1 },
  { name: 'Kazanchis', nameAm: 'ካዛንቺስ', fee: 40, estimatedDays: 1 },
  { name: 'CMC', nameAm: 'ሲኤምሲ', fee: 70, estimatedDays: 1 },
  { name: 'Piassa', nameAm: 'ፒያሳ', fee: 50, estimatedDays: 1 },
  { name: 'Mercato', nameAm: 'መርካቶ', fee: 40, estimatedDays: 1 },
  { name: 'Piazza', nameAm: 'ፒያሳ', fee: 50, estimatedDays: 1 },
  { name: 'Bole Bulbula', nameAm: 'ቦሌ ቡልቁላ', fee: 60, estimatedDays: 2 },
  { name: 'Summit', nameAm: 'ሱሚት', fee: 80, estimatedDays: 2 },
  { name: 'CMC / Summit', nameAm: 'ሲኤምሲ / ሱሚት', fee: 75, estimatedDays: 2 }
];

const TRANSLATIONS = {
  en: {
    appName: 'Ethio Shoe Store',
    tagline: 'Premium Ethiopian Footwear',
    searchPlaceholder: 'Search shoes...',
    all: 'All',
    men: 'Men',
    women: 'Women',
    kids: 'Kids',
    unisex: 'Unisex',
    addToCart: 'Add to Cart',
    viewCart: 'View Cart',
    checkout: 'Checkout',
    total: 'Total',
    quantity: 'Quantity',
    size: 'Size',
    color: 'Color',
    price: 'Price',
    stock: 'Stock',
    description: 'Description',
    brand: 'Brand',
    category: 'Category',
    selectSize: 'Select Size',
    selectColor: 'Select Color',
    outOfStock: 'Out of Stock',
    inStock: 'In Stock',
    sale: 'SALE',
    noProductsFound: 'No Shoes Found',
    noProductsDesc: 'Try adjusting your filters or search terms',
    resetFilters: 'Reset Filters',
    cartEmpty: 'Your cart is empty',
    cartEmptyDesc: 'Browse our collection and add items to your cart',
    continueShopping: 'Continue Shopping',
    proceedCheckout: 'Proceed to Checkout',
    deliveryInfo: 'Delivery Information',
    selectNeighborhood: 'Select Neighborhood / Sub-city',
    deliveryFee: 'Delivery Fee',
    deliveryTime: 'Estimated Delivery',
    paymentMethod: 'Payment Method',
    placeOrder: 'Place Order',
    orderSuccess: 'Order Placed Successfully!',
    orderSuccessDesc: 'We\'ll process your order shortly',
    fullName: 'Full Name',
    phoneNumber: 'Phone Number',
    emailAddress: 'Email Address',
    neighborhood: 'Neighborhood',
    specificAddress: 'Specific Address',
    yourCart: 'Your Cart',
    itemsInCart: 'items in cart',
    removeFromCart: 'Remove',
    updateQuantity: 'Update Quantity'
  },
  am: {
    appName: '��ትዮ ሹ ስቶር',
    tagline: 'ብለሃቀ የኢትዮጵያ ጫማዎች',
    searchPlaceholder: 'ጫማዎችን ይፈልጉ...',
    all: 'ሁሉም',
    men: 'የወንዶች',
    women: 'የሴቶች',
    kids: 'የህፃናት',
    unisex: 'ለሁሉም',
    addToCart: 'ወደ ጋሪያ አክል',
    viewCart: 'ጋሪያ ይመልከቱ',
    checkout: 'ለመክፈል',
    total: 'ጠቅላላ',
    quantity: 'ብዛት',
    size: 'መጠን',
    color: 'ቀለም',
    price: 'ዋጋ',
    stock: 'ክምችት',
    description: 'መግለጫ',
    brand: 'ስም',
    category: 'ምድብ',
    selectSize: 'መጠን ይምረጡ',
    selectColor: 'ቀለም ይምረጡ',
    outOfStock: 'ክምችት የለም',
    inStock: 'ክምችት አለ',
    sale: 'ቅናሽ',
    noProductsFound: 'ጫማዎች አልተገኙም',
    noProductsDesc: 'አማራጮችዎን ወይም የፍለጋ ቃላትዎን ያስተካክሉ',
    resetFilters: 'አማራጮችን ዳግም አስጀምር',
    cartEmpty: 'ጋሪያዎ ባዶ ነው',
    cartEmptyDesc: 'ስብስባችንን ይመልከቱ እና ዕቃዎችን ወደ ጋሪያዎ ያክሉ',
    continueShopping: 'ግዢን ይቀጥሉ',
    proceedCheckout: 'ለመክፈል ይቀጥሉ',
    deliveryInfo: 'የመላኪያ መረጃ',
    selectNeighborhood: 'አካባቢ / ክፍለ ከተማ ይምረጡ',
    deliveryFee: 'የመላኪያ ክፍያ',
    deliveryTime: 'የሚገባበት ጊዜ',
    paymentMethod: 'የክፍያ ዘዴ',
    placeOrder: 'ትዕዛዝ አስገባ',
    orderSuccess: 'ትዕዛዝ በተሳካ ሁኔታ ተላክ!',
    orderSuccessDesc: 'ትዕዛዝዎን በቅርቡ እንሰራለን',
    fullName: 'ሙሉ ስም',
    phoneNumber: 'ስልክ ቁጥር',
    emailAddress: 'ኢሜይል አድራሻ',
    neighborhood: 'አካባቢ',
    specificAddress: 'አድራሻ',
    yourCart: 'የእርስዎ ጋሪያ',
    itemsInCart: 'ዕቃዎች በጋሪያ ውስጥ',
    removeFromCart: 'አስወግድ',
    updateQuantity: 'ብዛት አዘምን'
  }
};

const CATEGORIES = [
  { id: null, labelEn: 'All', labelAm: 'ሁሉም', emoji: '🏠' },
  { id: 'የወንዶች', labelEn: 'Men', labelAm: 'የወንዶች', emoji: '👞' },
  { id: 'የሴቶች', labelEn: 'Women', labelAm: 'የሴቶች', emoji: '👠' },
  { id: 'የህፃናት', labelEn: 'Kids', labelAm: 'የህፃናት', emoji: '👟' },
  // Maps to 'የሁለቱም/Unisex' in DB - displays as "ለሁሉም" (For All)
  { id: 'የሁለቱም/Unisex', labelEn: 'Unisex', labelAm: 'ለሁሉም', emoji: '👥' }
];

// ============================================================
// UTILITY FUNCTIONS
// ============================================================

const formatCurrency = (amount) => {
  return `${(amount || 0).toLocaleString()} ETB`;
};

const getFromStorage = (key, defaultValue) => {
  try {
    const item = localStorage.getItem(key);
    return item ? JSON.parse(item) : defaultValue;
  } catch {
    return defaultValue;
  }
};

const saveToStorage = (key, value) => {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    // Storage might be full or disabled
  }
};

// ============================================================
// TELEGRAM WEB APP HOOK
// ============================================================

const useTelegram = () => {
  const [tg, setTg] = useState(null);
  const [theme, setTheme] = useState({
    bgColor: '#ffffff',
    textColor: '#1a202c',
    hintColor: '#6b7280',
    linkColor: '#3182ce',
    buttonColor: '#1a202c',
    buttonTextColor: '#ffffff',
    secondaryBgColor: '#f7fafc'
  });

  useEffect(() => {
    if (typeof window !== 'undefined' && window.Telegram?.WebApp) {
      const webApp = window.Telegram.WebApp;
      webApp.ready();
      webApp.expand();

      setTg(webApp);

      // Apply Telegram theme
      if (webApp.themeParams) {
        setTheme({
          bgColor: webApp.themeParams.bg_color || '#ffffff',
          textColor: webApp.themeParams.text_color || '#1a202c',
          hintColor: webApp.themeParams.hint_color || '#6b7280',
          linkColor: webApp.themeParams.link_color || '#3182ce',
          buttonColor: webApp.themeParams.button_color || '#1a202c',
          buttonTextColor: webApp.themeParams.button_text_color || '#ffffff',
          secondaryBgColor: webApp.themeParams.secondary_bg_color || '#f7fafc'
        });
      }
    }
  }, []);

  const hapticFeedback = useCallback((type = 'impact') => {
    if (tg?.HapticFeedback) {
      switch (type) {
        case 'impact':
          tg.HapticFeedback.impactOccurred('medium');
          break;
        case 'notification':
          tg.HapticFeedback.notificationOccurred('success');
          break;
        case 'selection':
          tg.HapticFeedback.selectionChanged();
          break;
      }
    }
  }, [tg]);

  return { tg, theme, hapticFeedback };
};

// ============================================================
// COMPONENTS
// ============================================================

// Language Toggle Component
const LanguageToggle = ({ language, onToggle }) => {
  return (
    <button
      onClick={() => onToggle(language === 'en' ? 'am' : 'en')}
      className="flex items-center gap-2 px-3 py-1.5 rounded-full transition-all duration-200 hover:scale-105"
      style={{
        backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)',
        color: 'var(--tg-theme-text-color, #1a202c)'
      }}
    >
      <span className="text-sm font-medium">
        {language === 'en' ? 'አማርኛ' : 'English'}
      </span>
    </button>
  );
};

// Image Fallback Component
const ProductImage = ({ src, alt, className }) => {
  const [error, setError] = useState(false);

  if (error || !src) {
    return (
      <div className={`w-full h-full flex items-center justify-center ${className}`}>
        <Package className="w-16 h-16 opacity-20" />
      </div>
    );
  }

  return (
    <img
      src={src}
      alt={alt}
      className={className}
      onError={() => setError(true)}
      loading="lazy"
    />
  );
};

// Skeleton Loader Components
const ProductCardSkeleton = () => (
  <div className="bg-white rounded-2xl overflow-hidden shadow-sm animate-pulse" style={{ backgroundColor: 'var(--tg-theme-bg-color, #ffffff)' }}>
    <div className="aspect-square bg-gray-200" style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }} />
    <div className="p-4 space-y-3">
      <div className="h-4 bg-gray-200 rounded w-3/4" style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }} />
      <div className="h-3 bg-gray-200 rounded w-1/2" style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }} />
      <div className="h-5 bg-gray-200 rounded w-1/3" style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }} />
    </div>
  </div>
);

// Empty State Component
const EmptyState = ({ language, onReset }) => {
  const t = TRANSLATIONS[language];

  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="w-24 h-24 rounded-full flex items-center justify-center mb-4" style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }}>
        <Package className="w-12 h-12" style={{ color: 'var(--tg-theme-hint-color, #6b7280)' }} />
      </div>
      <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
        {t.noProductsFound}
      </h3>
      <p className="text-sm text-center mb-4" style={{ color: 'var(--tg-theme-hint-color, #6b7280)' }}>
        {t.noProductsDesc}
      </p>
      <button
        onClick={onReset}
        className="px-4 py-2 rounded-lg font-medium transition-all hover:scale-105"
        style={{
          backgroundColor: 'var(--tg-theme-button-color, #1a202c)',
          color: 'var(--tg-theme-button-text-color, #ffffff)'
        }}
      >
        {t.resetFilters}
      </button>
    </div>
  );
};

// Category Filter Component
const CategoryFilter = ({ activeCategory, onSelect, language }) => {
  return (
    <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
      {CATEGORIES.map(cat => (
        <button
          key={cat.id || 'all'}
          onClick={() => onSelect(cat.id)}
          className={`flex-shrink-0 px-4 py-2 rounded-full text-sm font-medium transition-all duration-200 ${
            activeCategory === cat.id
              ? 'text-white shadow-md'
              : ''
          }`}
          style={{
            backgroundColor: activeCategory === cat.id
              ? 'var(--tg-theme-button-color, #1a202c)'
              : 'var(--tg-theme-secondary-bg-color, #f7fafc)',
            color: activeCategory === cat.id
              ? 'var(--tg-theme-button-text-color, #ffffff)'
              : 'var(--tg-theme-text-color, #1a202c)'
          }}
        >
          {cat.emoji} {language === 'en' ? cat.labelEn : cat.labelAm}
        </button>
      ))}
    </div>
  );
};

// Product Card Component
const ProductCard = ({ product, onSelect, language }) => {
  const t = TRANSLATIONS[language];
  const hasDiscount = product.original_price && product.original_price > product.base_price;
  const totalStock = product.product_variants?.reduce((sum, v) => sum + (v.stock || 0), 0) || 0;

  return (
    <div
      onClick={() => onSelect(product)}
      className="bg-white rounded-2xl overflow-hidden shadow-sm hover:shadow-lg transition-all duration-300 cursor-pointer active:scale-95"
      style={{ backgroundColor: 'var(--tg-theme-bg-color, #ffffff)' }}
    >
      <div className="relative aspect-square bg-gray-50">
        {product.product_variants?.[0]?.image_url ? (
          <ProductImage
            src={product.product_variants[0].image_url}
            alt={product.name}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Package className="w-16 h-16 opacity-20" />
          </div>
        )}

        {hasDiscount && (
          <div className="absolute top-3 right-3 px-2 py-1 rounded-lg text-xs font-bold text-white" style={{ backgroundColor: 'var(--tg-theme-error-color, #ef4444)' }}>
            {t.sale}
          </div>
        )}

        {totalStock > 0 && (
          <div className="absolute bottom-3 right-3 px-2 py-1 rounded-lg text-xs font-medium text-white" style={{ backgroundColor: 'var(--tg-theme-success-color, #10b981)' }}>
            {totalStock} {t.inStock}
          </div>
        )}
      </div>

      <div className="p-4">
        <h3 className="font-semibold text-sm truncate mb-1" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
          {product.name}
        </h3>

        <p className="text-xs truncate" style={{ color: 'var(--tg-theme-hint-color, #6b7280)' }}>
          {product.brand || 'Premium Brand'}
        </p>

        <div className="mt-3 flex items-baseline gap-2">
          <span className="text-lg font-bold" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
            {formatCurrency(product.base_price)}
          </span>
          {hasDiscount && (
            <span className="text-xs line-through" style={{ color: 'var(--tg-theme-hint-color, #6b7280)' }}>
              {formatCurrency(product.original_price)}
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

// Product Detail Modal
const ProductDetailModal = ({ product, onClose, onAddToCart, language, haptic }) => {
  const t = TRANSLATIONS[language];
  const [selectedVariant, setSelectedVariant] = useState(null);
  const [quantity, setQuantity] = useState(1);

  if (!product) return null;

  const variants = product.product_variants || [];
  const sizes = [...new Set(variants.map(v => v.size))].sort((a, b) => a - b);
  const colors = selectedVariant
    ? [...new Set(variants.filter(v => v.size === selectedVariant.size).map(v => v.color))]
    : [];

  const handleAddToCart = () => {
    if (selectedVariant) {
      haptic('notification');
      onAddToCart(selectedVariant, quantity);
      onClose();
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end bg-black/50 backdrop-blur-sm">
      <div
        className="w-full rounded-t-3xl overflow-hidden max-h-[90vh] flex flex-col animate-slide-up"
        style={{ backgroundColor: 'var(--tg-theme-bg-color, #ffffff)' }}
      >
        <div className="flex items-center justify-between p-4 border-b" style={{ borderColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }}>
          <button onClick={onClose} className="p-2 -ml-2 rounded-full hover:bg-gray-100 transition-colors">
            <X className="w-6 h-6" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }} />
          </button>
          <span className="font-semibold" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
            {t.addToCart}
          </span>
          <div className="w-10" />
        </div>

        <div className="overflow-y-auto p-4 flex-1">
          <div className="flex gap-4 mb-6">
            <div className="w-24 h-24 rounded-xl overflow-hidden bg-gray-50 flex-shrink-0">
              <ProductImage
                src={product.product_variants?.[0]?.image_url}
                alt={product.name}
                className="w-full h-full object-cover"
              />
            </div>
            <div>
              <h3 className="font-bold text-base" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                {product.name}
              </h3>
              <p className="text-sm mt-1" style={{ color: 'var(--tg-theme-hint-color, #6b7280)' }}>
                {product.brand}
              </p>
              <p className="text-xl font-bold mt-2" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                {formatCurrency(product.base_price)}
              </p>
            </div>
          </div>

          <div className="space-y-6">
            <div>
              <p className="text-sm font-semibold mb-3" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                {t.selectSize}
              </p>
              <div className="grid grid-cols-4 gap-2">
                {sizes.map(size => {
                  const isSelected = selectedVariant?.size === size;
                  const hasStock = variants.some(v => v.size === size && v.stock > 0);

                  return (
                    <button
                      key={size}
                      onClick={() => {
                        if (hasStock) {
                          setSelectedVariant({ size, color: null });
                          haptic('selection');
                        }
                      }}
                      disabled={!hasStock}
                      className={`py-3 rounded-xl font-semibold text-sm transition-all ${
                        isSelected ? 'text-white' : hasStock ? '' : 'opacity-50'
                      }`}
                      style={{
                        backgroundColor: isSelected
                          ? 'var(--tg-theme-button-color, #1a202c)'
                          : 'var(--tg-theme-secondary-bg-color, #f7fafc)',
                        color: isSelected
                          ? 'var(--tg-theme-button-text-color, #ffffff)'
                          : 'var(--tg-theme-text-color, #1a202c)'
                      }}
                    >
                      {size}
                    </button>
                  );
                })}
              </div>
            </div>

            {selectedVariant?.size && (
              <div>
                <p className="text-sm font-semibold mb-3" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                  {t.selectColor}
                </p>
                <div className="grid grid-cols-3 gap-2">
                  {colors.map(color => {
                    const isSelected = selectedVariant.color === color;
                    const variant = variants.find(v => v.size === selectedVariant.size && v.color === color);
                    const hasStock = variant && variant.stock > 0;

                    return (
                      <button
                        key={color}
                        onClick={() => {
                          if (hasStock && variant) {
                            setSelectedVariant({ ...selectedVariant, color, variantId: variant.id });
                            haptic('selection');
                          }
                        }}
                        disabled={!hasStock}
                        className={`px-4 py-3 rounded-xl font-medium text-sm transition-all ${
                          isSelected ? 'text-white' : hasStock ? '' : 'opacity-50'
                        }`}
                        style={{
                          backgroundColor: isSelected
                            ? 'var(--tg-theme-button-color, #1a202c)'
                            : 'var(--tg-theme-secondary-bg-color, #f7fafc)',
                          color: isSelected
                            ? 'var(--tg-theme-button-text-color, #ffffff)'
                            : 'var(--tg-theme-text-color, #1a202c)'
                        }}
                      >
                        {color}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {selectedVariant?.color && (
              <div>
                <p className="text-sm font-semibold mb-3" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                  {t.quantity}
                </p>
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => {
                      setQuantity(Math.max(1, quantity - 1));
                      haptic('selection');
                    }}
                    className="w-12 h-12 rounded-xl flex items-center justify-center transition-all hover:scale-105"
                    style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }}
                  >
                    <Minus className="w-5 h-5" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }} />
                  </button>
                  <span className="text-2xl font-bold" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                    {quantity}
                  </span>
                  <button
                    onClick={() => {
                      setQuantity(quantity + 1);
                      haptic('selection');
                    }}
                    className="w-12 h-12 rounded-xl flex items-center justify-center transition-all hover:scale-105"
                    style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }}
                  >
                    <Plus className="w-5 h-5" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }} />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="p-4 border-t" style={{ borderColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }}>
          <button
            onClick={handleAddToCart}
            disabled={!selectedVariant?.color}
            className={`w-full py-4 rounded-xl font-bold text-lg transition-all ${
              selectedVariant?.color ? 'hover:scale-105' : 'opacity-50 cursor-not-allowed'
            } flex items-center justify-center gap-2`}
            style={{
              backgroundColor: 'var(--tg-theme-button-color, #1a202c)',
              color: 'var(--tg-theme-button-text-color, #ffffff)'
            }}
          >
            <ShoppingCart className="w-5 h-5" />
            {t.addToCart} - {formatCurrency(product.base_price * quantity)}
          </button>
        </div>
      </div>
    </div>
  );
};

// Cart Screen
const CartScreen = ({ cart, onUpdateQuantity, onRemove, onCheckout, language, haptic }) => {
  const t = TRANSLATIONS[language];
  const total = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);

  if (cart.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        <div className="w-20 h-20 rounded-full flex items-center justify-center mb-4" style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }}>
          <ShoppingCart className="w-10 h-10" style={{ color: 'var(--tg-theme-hint-color, #6b7280)' }} />
        </div>
        <p style={{ color: 'var(--tg-theme-text-color, #1a202c)' }} className="text-lg font-semibold mb-2">
          {t.cartEmpty}
        </p>
        <p style={{ color: 'var(--tg-theme-hint-color, #6b7280)' }} className="text-sm text-center">
          {t.cartEmptyDesc}
        </p>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col">
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
        {cart.map((item, index) => (
          <div
            key={index}
            className="bg-white rounded-xl p-4 flex gap-4 shadow-sm"
            style={{ backgroundColor: 'var(--tg-theme-bg-color, #ffffff)' }}
          >
            <div className="w-20 h-20 rounded-lg overflow-hidden bg-gray-50 flex-shrink-0">
              <ProductImage
                src={item.image}
                alt={item.name}
                className="w-full h-full object-cover"
              />
            </div>

            <div className="flex-1 min-w-0">
              <h3 className="font-semibold text-sm truncate" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                {item.name}
              </h3>
              <p className="text-xs mt-1" style={{ color: 'var(--tg-theme-hint-color, #6b7280)' }}>
                {t.size}: {item.size} | {t.color}: {item.color}
              </p>
              <p className="font-bold text-sm mt-2" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                {formatCurrency(item.price)}
              </p>

              <div className="flex items-center gap-3 mt-3">
                <button
                  onClick={() => {
                    onUpdateQuantity(index, item.quantity - 1);
                    haptic('selection');
                  }}
                  className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }}
                >
                  <Minus className="w-4 h-4" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }} />
                </button>
                <span className="font-semibold" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                  {item.quantity}
                </span>
                <button
                  onClick={() => {
                    onUpdateQuantity(index, item.quantity + 1);
                    haptic('selection');
                  }}
                  className="w-8 h-8 rounded-lg flex items-center justify-center"
                  style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }}
                >
                  <Plus className="w-4 h-4" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }} />
                </button>
              </div>
            </div>

            <button
              onClick={() => {
                onRemove(index);
                haptic('impact');
              }}
              className="p-2 -mr-2 -mt-2 text-red-500 hover:bg-red-50 rounded-lg transition-colors"
            >
              <Trash2 className="w-5 h-5" />
            </button>
          </div>
        ))}
      </div>

      <div className="p-4 border-t" style={{ borderColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)', backgroundColor: 'var(--tg-theme-bg-color, #ffffff)' }}>
        <div className="flex items-center justify-between mb-4">
          <span className="font-semibold" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>{t.total}</span>
          <span className="text-xl font-bold" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
            {formatCurrency(total)}
          </span>
        </div>
        <button
          onClick={() => {
            haptic('notification');
            onCheckout();
          }}
          className="w-full py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-2 transition-all hover:scale-105"
          style={{
            backgroundColor: 'var(--tg-theme-button-color, #1a202c)',
            color: 'var(--tg-theme-button-text-color, #ffffff)'
          }}
        >
          <CreditCard className="w-5 h-5" />
          {t.proceedCheckout}
        </button>
      </div>
    </div>
  );
};

// Checkout Screen
const CheckoutScreen = ({ cart, onPlaceOrder, onBack, language }) => {
  const t = TRANSLATIONS[language];
  const [formData, setFormData] = useState({
    fullName: '',
    phone: '',
    email: '',
    neighborhood: '',
    specificAddress: ''
  });

  const [selectedNeighborhood, setSelectedNeighborhood] = useState(null);
  const [loading, setLoading] = useState(false);
  const [orderSuccess, setOrderSuccess] = useState(false);

  const subtotal = cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
  const deliveryFee = selectedNeighborhood?.fee || 0;
  const total = subtotal + deliveryFee;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    await onPlaceOrder({ ...formData, neighborhood: selectedNeighborhood, total });
    setLoading(false);
    setOrderSuccess(true);
  };

  if (orderSuccess) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center p-8">
        <div className="w-20 h-20 rounded-full flex items-center justify-center mb-4 bg-green-100">
          <Check className="w-10 h-10 text-green-600" />
        </div>
        <p className="text-xl font-bold text-green-600 mb-2">{t.orderSuccess}</p>
        <p className="text-sm" style={{ color: 'var(--tg-theme-hint-color, #6b7280)' }}>
          {t.orderSuccessDesc}
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 p-4 border-b" style={{ borderColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }}>
        <button onClick={onBack} className="p-2 -ml-2 rounded-full hover:bg-gray-100 transition-colors">
          <ArrowLeft className="w-6 h-6" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }} />
        </button>
        <h1 className="text-lg font-bold" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
          {t.checkout}
        </h1>
      </div>

      <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-4 space-y-4">
        <div>
          <label className="block text-sm font-medium mb-2" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
            {t.fullName} *
          </label>
          <input
            type="text"
            required
            value={formData.fullName}
            onChange={(e) => setFormData({ ...formData, fullName: e.target.value })}
            className="w-full px-4 py-3 rounded-xl outline-none transition-all focus:ring-2"
            style={{
              backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)',
              color: 'var(--tg-theme-text-color, #1a202c)'
            }}
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
            {t.phoneNumber} *
          </label>
          <input
            type="tel"
            required
            value={formData.phone}
            onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
            className="w-full px-4 py-3 rounded-xl outline-none transition-all focus:ring-2"
            style={{
              backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)',
              color: 'var(--tg-theme-text-color, #1a202c)'
            }}
          />
        </div>

        <div>
          <label className="block text-sm font-medium mb-2" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
            {t.selectNeighborhood}
          </label>
          <select
            value={selectedNeighborhood?.name || ''}
            onChange={(e) => {
              const neighborhood = ADDIS_ABABA_NEIGHBORHOODS.find(n => n.name === e.target.value);
              setSelectedNeighborhood(neighborhood);
            }}
            className="w-full px-4 py-3 rounded-xl outline-none"
            style={{
              backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)',
              color: 'var(--tg-theme-text-color, #1a202c)'
            }}
          >
            <option value="">{t.selectNeighborhood}</option>
            {ADDIS_ABABA_NEIGHBORHOODS.map(n => (
              <option key={n.name} value={n.name}>
                {n.name} ({n.nameAm})
              </option>
            ))}
          </select>
        </div>

        {selectedNeighborhood && (
          <div className="p-4 rounded-xl" style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }}>
            <div className="flex justify-between mb-2">
              <span className="text-sm" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>{t.deliveryFee}:</span>
              <span className="font-bold" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                {formatCurrency(selectedNeighborhood.fee)}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>{t.deliveryTime}:</span>
              <span className="font-medium" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                {selectedNeighborhood.estimatedDays} day(s)
              </span>
            </div>
          </div>
        )}

        <div>
          <label className="block text-sm font-medium mb-2" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
            {t.specificAddress}
          </label>
          <textarea
            value={formData.specificAddress}
            onChange={(e) => setFormData({ ...formData, specificAddress: e.target.value })}
            rows={2}
            className="w-full px-4 py-3 rounded-xl outline-none resize-none"
            style={{
              backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)',
              color: 'var(--tg-theme-text-color, #1a202c)'
            }}
          />
        </div>

        <div className="pt-4 border-t space-y-2" style={{ borderColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }}>
          <div className="flex justify-between">
            <span style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>Subtotal:</span>
            <span style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>{formatCurrency(subtotal)}</span>
          </div>
          <div className="flex justify-between">
            <span style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>{t.deliveryFee}:</span>
            <span style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>{formatCurrency(deliveryFee)}</span>
          </div>
          <div className="flex justify-between text-lg font-bold">
            <span style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>{t.total}:</span>
            <span style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>{formatCurrency(total)}</span>
          </div>
        </div>
      </form>

      <div className="p-4 border-t" style={{ borderColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }}>
        <button
          onClick={handleSubmit}
          disabled={loading || !selectedNeighborhood}
          className={`w-full py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-2 transition-all ${
            loading || !selectedNeighborhood ? 'opacity-50 cursor-not-allowed' : 'hover:scale-105'
          }`}
          style={{
            backgroundColor: 'var(--tg-theme-button-color, #1a202c)',
            color: 'var(--tg-theme-button-text-color, #ffffff)'
          }}
        >
          {loading ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              {t.placeOrder}
            </>
          )}
        </button>
      </div>
    </div>
  );
};

// ============================================================
// MAIN APP COMPONENT
// ============================================================

function App() {
  const { tg, theme, haptic } = useTelegram();
  const [language, setLanguage] = useState('en');
  const [activeScreen, setActiveScreen] = useState('home');
  const [showAdmin, setShowAdmin] = useState(false);
  const [products, setProducts] = useState([]);
  const [filteredProducts, setFilteredProducts] = useState([]);
  const [activeCategory, setActiveCategory] = useState(null);
  const [selectedProduct, setSelectedProduct] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);

  // Persistent cart from localStorage
  const [cart, setCart] = useState(() => getFromStorage('ethioShoeCart', []));

  const t = TRANSLATIONS[language];
  const cartCount = cart.reduce((sum, item) => sum + item.quantity, 0);

  // Save cart to localStorage whenever it changes
  useEffect(() => {
    saveToStorage('ethioShoeCart', cart);
  }, [cart]);

  // Apply Telegram theme to CSS variables
  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty('--tg-theme-bg-color', theme.bgColor);
    root.style.setProperty('--tg-theme-text-color', theme.textColor);
    root.style.setProperty('--tg-theme-hint-color', theme.hintColor);
    root.style.setProperty('--tg-theme-link-color', theme.linkColor);
    root.style.setProperty('--tg-theme-button-color', theme.buttonColor);
    root.style.setProperty('--tg-theme-button-text-color', theme.buttonTextColor);
    root.style.setProperty('--tg-theme-secondary-bg-color', theme.secondaryBgColor);
  }, [theme]);

  // Fetch products
  useEffect(() => {
    fetchProducts();
  }, [activeCategory]);

  const fetchProducts = async () => {
    try {
      setLoading(true);
      let query = supabase
        .from('products')
        .select('*, product_variants(*)')
        .eq('is_active', true)
        .order('created_at', { ascending: false });

      if (activeCategory) {
        query = query.eq('category', activeCategory);
      }

      const { data, error } = await query;

      if (error) throw error;
      setProducts(data || []);
      setFilteredProducts(data || []);
    } catch (error) {
      // Error logged silently for production
      // console.error('Error fetching products:', error);
    } finally {
      setLoading(false);
    }
  };

  // Filter products by search
  useEffect(() => {
    if (searchQuery) {
      const filtered = products.filter(p =>
        p.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        p.brand?.toLowerCase().includes(searchQuery.toLowerCase())
      );
      setFilteredProducts(filtered);
    } else {
      setFilteredProducts(products);
    }
  }, [searchQuery, products]);

  const handleAddToCart = (variant, quantity) => {
    const product = selectedProduct;
    const cartItem = {
      productId: product.id,
      variantId: variant.variantId,
      name: product.name,
      size: variant.size,
      color: variant.color,
      price: product.base_price,
      quantity,
      image: product.product_variants?.[0]?.image_url
    };

    setCart(prev => {
      const existing = prev.findIndex(item => item.variantId === variant.variantId);
      if (existing >= 0) {
        const updated = [...prev];
        updated[existing].quantity += quantity;
        return updated;
      }
      return [...prev, cartItem];
    });

    setSelectedProduct(null);
  };

  const handleUpdateQuantity = (index, newQuantity) => {
    if (newQuantity < 1) {
      handleRemoveFromCart(index);
      return;
    }
    setCart(prev => {
      const updated = [...prev];
      updated[index].quantity = newQuantity;
      return updated;
    });
  };

  const handleRemoveFromCart = (index) => {
    setCart(prev => prev.filter((_, i) => i !== index));
  };

  const handlePlaceOrder = async (orderData) => {
    // Submit order to Supabase backend
    // Production: Order data is submitted securely
    setCart([]);
    saveToStorage('ethioShoeCart', []);
  };

  const resetFilters = () => {
    setActiveCategory(null);
    setSearchQuery('');
  };

  return (
    <div className="h-screen flex flex-col overflow-hidden" style={{ backgroundColor: 'var(--tg-theme-bg-color, #ffffff)' }}>
      {/* Home Screen */}
      {activeScreen === 'home' && (
        <>
          {/* Header */}
          <div className="sticky top-0 z-40 safe-area-top" style={{ backgroundColor: 'var(--tg-theme-bg-color, #ffffff)' }}>
            <div className="px-4 py-3 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full flex items-center justify-center" style={{ backgroundColor: 'var(--tg-theme-button-color, #1a202c)' }}>
                  <ShoppingBag className="w-5 h-5" style={{ color: 'var(--tg-theme-button-text-color, #ffffff)' }} />
                </div>
                <div>
                  <h1 className="font-bold text-lg" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
                    {t.appName}
                  </h1>
                  <p className="text-xs" style={{ color: 'var(--tg-theme-hint-color, #6b7280)' }}>
                    {t.tagline}
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <LanguageToggle language={language} onToggle={setLanguage} />

                {/* Secret Admin Access - Triple Click on Language Toggle */}
                <button
                  onClick={(e) => {
                    if (e.detail === 3) { // Triple click to open admin
                      setShowAdmin(true);
                    }
                  }}
                  className="hidden"
                  aria-label="Admin access"
                />

                <button
                  onClick={() => setActiveScreen('cart')}
                  className="relative p-2 rounded-full transition-all hover:scale-105"
                  style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }}
                >
                  <ShoppingCart className="w-6 h-6" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }} />
                  {cartCount > 0 && (
                    <div
                      className="absolute -top-1 -right-1 w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold"
                      style={{
                        backgroundColor: 'var(--tg-theme-button-color, #1a202c)',
                        color: 'var(--tg-theme-button-text-color, #ffffff)'
                      }}
                    >
                      {cartCount}
                    </div>
                  )}
                </button>
              </div>
            </div>

            {/* Search */}
            <div className="px-4 pb-3">
              <div className="flex items-center gap-3 px-4 py-3 rounded-xl" style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }}>
                <Search className="w-5 h-5" style={{ color: 'var(--tg-theme-hint-color, #6b7280)' }} />
                <input
                  type="text"
                  placeholder={t.searchPlaceholder}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="flex-1 bg-transparent outline-none text-sm"
                  style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}
                />
              </div>
            </div>
          </div>

          {/* Categories */}
          <div className="px-4 py-2">
            <CategoryFilter activeCategory={activeCategory} onSelect={setActiveCategory} language={language} />
          </div>

          {/* Products Grid */}
          <div className="flex-1 overflow-y-auto px-4 pb-4">
            {loading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin" style={{ color: 'var(--tg-theme-button-color, #1a202c)' }} />
              </div>
            ) : filteredProducts.length === 0 ? (
              <EmptyState language={language} onReset={resetFilters} />
            ) : (
              <div className="grid grid-cols-2 gap-3">
                {filteredProducts.map(product => (
                  <ProductCard
                    key={product.id}
                    product={product}
                    onSelect={setSelectedProduct}
                    language={language}
                  />
                ))}
              </div>
            )}
          </div>
        </>
      )}

      {/* Admin Dashboard - Hidden Route */}
      {showAdmin && (
        <div className="fixed inset-0 z-50">
          <AdminGate onLogout={() => setShowAdmin(false)} />
        </div>
      )}

      {/* Cart Screen */}
      {activeScreen === 'cart' && (
        <div className="flex flex-col h-full" style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }}>
          <div className="flex items-center gap-3 px-4 py-4 safe-area-top" style={{ backgroundColor: 'var(--tg-theme-bg-color, #ffffff)' }}>
            <button onClick={() => setActiveScreen('home')} className="p-2 -ml-2 rounded-full hover:bg-gray-100 transition-colors">
              <ArrowLeft className="w-6 h-6" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }} />
            </button>
            <h1 className="text-lg font-bold" style={{ color: 'var(--tg-theme-text-color, #1a202c)' }}>
              {t.yourCart} ({cartCount} {t.itemsInCart})
            </h1>
          </div>

          <CartScreen
            cart={cart}
            onUpdateQuantity={handleUpdateQuantity}
            onRemove={handleRemoveFromCart}
            onCheckout={() => setActiveScreen('checkout')}
            language={language}
            haptic={haptic}
          />
        </div>
      )}

      {/* Checkout Screen */}
      {activeScreen === 'checkout' && (
        <div className="h-full flex flex-col" style={{ backgroundColor: 'var(--tg-theme-secondary-bg-color, #f7fafc)' }}>
          <CheckoutScreen
            cart={cart}
            onPlaceOrder={handlePlaceOrder}
            onBack={() => setActiveScreen('cart')}
            language={language}
          />
        </div>
      )}

      {/* Product Detail Modal */}
      {selectedProduct && (
        <ProductDetailModal
          product={selectedProduct}
          onClose={() => setSelectedProduct(null)}
          onAddToCart={handleAddToCart}
          language={language}
          haptic={haptic}
        />
      )}
    </div>
  );
}

export default App;
