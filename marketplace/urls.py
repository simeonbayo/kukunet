# marketplace/urls.py - Updated with agribusiness API endpoints
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

# Register all viewsets with explicit basenames to avoid any issues
router.register('products', views.ProductViewSet, basename='product')
router.register('cart', views.CartViewSet, basename='cart')
router.register('orders', views.OrderViewSet, basename='order')
router.register('admin/orders', views.AdminOrderViewSet, basename='admin-order')
router.register('promotions', views.PromotionViewSet, basename='promotion')
router.register('shipping', views.ShippingMethodViewSet, basename='shipping')
router.register('agribusiness', views.AgribusinessDashboardViewSet, basename='agribusiness')

urlpatterns = [
    path('', include(router.urls)),
    
    # ==================== AGRIBUSINESS API ENDPOINTS ====================
    # These endpoints are for AJAX calls from the agribusiness dashboard
    
    # Statistics and Dashboard Data
    path('agribusiness/stats/', views.agribusiness_stats_api, name='agribusiness_stats'),
    path('agribusiness/recent_orders/', views.agribusiness_recent_orders_api, name='agribusiness_recent_orders'),
    path('agribusiness/all_orders/', views.agribusiness_all_orders_api, name='agribusiness_all_orders'),
    path('agribusiness/low_stock_alerts/', views.agribusiness_low_stock_alerts_api, name='agribusiness_low_stock_alerts'),
    
    # Inventory and Product Management
    path('agribusiness/inventory/', views.agribusiness_inventory_api, name='agribusiness_inventory'),
    path('agribusiness/price_list/', views.agribusiness_price_list_api, name='agribusiness_price_list'),
    path('agribusiness/add_product/', views.agribusiness_add_product_api, name='agribusiness_add_product'),
    
    # Product Operations (with IDs)
    path('agribusiness/<int:product_id>/update_price/', views.agribusiness_update_price_api, name='agribusiness_update_price'),
    path('agribusiness/<int:product_id>/update/', views.agribusiness_update_product_api, name='agribusiness_update_product'),
    path('agribusiness/<int:product_id>/restock/', views.agribusiness_restock_product_api, name='agribusiness_restock'),
    path('agribusiness/<int:product_id>/delete_product/', views.agribusiness_delete_product_api, name='agribusiness_delete_product'),
    
    # Order Operations (with IDs)
    path('agribusiness/<int:order_id>/update_order_status/', views.agribusiness_update_order_status_api, name='agribusiness_update_order_status'),
]