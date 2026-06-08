# frontend/urls.py
from django.urls import path
from . import views

app_name = 'frontend'

urlpatterns = [
    # Authentication
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('logout-get/', views.logout_get_view, name='logout_get'),
    
    # Main dashboard
    path('', views.dashboard_view, name='home'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    
    # Role-based dashboards
    path('farmer/', views.farmer_dashboard_view, name='farmer_dashboard'),
    path('supplier/', views.supplier_dashboard_view, name='supplier_dashboard'),
    path('customer/', views.customer_dashboard_view, name='customer_dashboard'),
    path('trainer/', views.trainer_dashboard_view, name='trainer_dashboard'),
    path('field-officer/', views.field_officer_dashboard_view, name='field_officer_dashboard'),
    path('admin-dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    
    # Farm management URLs
    path('farm/', views.farm_management_view, name='farm_management'),
    path('farm/houses/', views.houses_view, name='houses'),
    path('farm/house/<int:house_id>/', views.house_details_view, name='house_details'),
    path('farm/flocks/', views.flocks_view, name='flocks'),
    path('farm/flock/<int:flock_id>/dashboard/', views.flock_dashboard_view, name='flock_dashboard'),
    path('farm/flock/<int:flock_id>/records/', views.flock_records_view, name='flock_records'),
    # Add this line
    path('farm/flock/<int:flock_id>/vaccinations/', views.vaccinations_view, name='flock_vaccinations'),
    path('farm/flock/<int:flock_id>/health/', views.health_monitoring_view, name='health_monitoring'),

    # Add this URL pattern
    path('farm/flock/<int:flock_id>/feed/', views.feed_management_view, name='feed_management'),
    
    # Organization type dashboards
    path('organization/', views.organization_default_dashboard_view, name='organization_default_dashboard'),
    path('organization/cooperative/', views.cooperative_dashboard_view, name='cooperative_dashboard'),
    path('organization/agribusiness/', views.agribusiness_dashboard_view, name='agribusiness_dashboard'),
    path('organization/ngo/', views.ngo_dashboard_view, name='ngo_dashboard'),
    path('organization/government/', views.government_dashboard_view, name='government_dashboard'),
    path('organization/research/', views.research_dashboard_view, name='research_dashboard'),

    # frontend/urls.py - Add shop URL
    path('shop/', views.shop_view, name='shop'),
    # Checkout
    path('checkout/', views.checkout_view, name='checkout'),
    # Order detail
    path('orders/<int:order_id>/', views.order_detail_view, name='order_detail'),


    # Aliases
    path('marketplace/', views.marketplace_view, name='marketplace'),

    # ==================== AGRIBUSINESS MANAGEMENT URLS ====================
    path('agribusiness/', views.agribusiness_dashboard_view, name='agribusiness_dashboard'),
    path('agribusiness/dashboard/', views.agribusiness_dashboard_view, name='agribusiness_dashboard'),
    path('agribusiness/products/', views.agribusiness_products_view, name='agribusiness_products'),
    path('agribusiness/products/add/', views.agribusiness_add_product_view, name='agribusiness_add_product'),
    path('agribusiness/products/<int:product_id>/edit/', views.agribusiness_edit_product_view, name='agribusiness_edit_product'),
    path('agribusiness/orders/', views.agribusiness_orders_view, name='agribusiness_orders'),
    # frontend/urls.py - Make sure this exists
    path('agribusiness/orders/<int:order_id>/', views.agribusiness_order_detail_view, name='agribusiness_order_detail'),
    path('agribusiness/inventory/', views.agribusiness_inventory_view, name='agribusiness_inventory'),
    path('agribusiness/price-list/', views.agribusiness_price_list_view, name='agribusiness_price_list'),
    path('courses/', views.courses_view, name='courses'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),
]

# Print for debugging
print("\n=== Frontend URLs Registered ===")
for url in urlpatterns:
    print(f"  {url.pattern}")
print("================================\n")