# frontend/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout as auth_logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
from django.utils import timezone

@ensure_csrf_cookie
def login_view(request):
    if request.user.is_authenticated:
        return redirect_role_based_dashboard(request.user)
    return render(request, 'auth/login.html')

@ensure_csrf_cookie
def register_view(request):
    if request.user.is_authenticated:
        return redirect_role_based_dashboard(request.user)
    return render(request, 'auth/register.html')

def redirect_role_based_dashboard(user):
    """Redirect users to their role-specific dashboard"""
    if user.role == 'SUPER_ADMIN':
        return redirect('/admin/')
    elif user.role == 'ADMIN':
        return redirect('frontend:admin_dashboard')
    elif user.role == 'FARMER':
        return redirect('frontend:farmer_dashboard')
    elif user.role == 'SUPPLIER':
        return redirect('frontend:supplier_dashboard')
    elif user.role == 'CUSTOMER':
        return redirect('frontend:customer_dashboard')
    elif user.role == 'TRAINER':
        return redirect('frontend:trainer_dashboard')
    elif user.role == 'FIELD_OFFICER':
        return redirect('frontend:field_officer_dashboard')
    elif user.role == 'ORGANIZATION':
        return redirect_organization_dashboard(user)
    else:
        return redirect('frontend:dashboard')

def redirect_organization_dashboard(user):
    """Redirect organization users to type-specific dashboard"""
    org_type = user.organization_type
    
    if org_type == 'COOPERATIVE':
        return redirect('frontend:cooperative_dashboard')
    elif org_type == 'AGRIBUSINESS':
        return redirect('frontend:agribusiness_dashboard')
    elif org_type == 'NGO':
        return redirect('frontend:ngo_dashboard')
    elif org_type == 'GOVERNMENT':
        return redirect('frontend:government_dashboard')
    elif org_type == 'RESEARCH':
        return redirect('frontend:research_dashboard')
    else:
        return redirect('frontend:organization_default_dashboard')

# ==================== MAIN DASHBOARD ====================

@login_required
def dashboard_view(request):
    """Default dashboard - redirect to role-specific dashboard"""
    return redirect_role_based_dashboard(request.user)

# ==================== FARMER DASHBOARDS ====================

@login_required
def farmer_dashboard_view(request):
    """Farmer dashboard - poultry farm management"""
    if request.user.role not in ['FARMER', 'ADMIN', 'SUPER_ADMIN']:
        return redirect_role_based_dashboard(request.user)
    
    farms = []
    flocks = []
    total_birds = 0
    today_eggs = 0
    mortality_rate = 0
    total_sales = 0
    
    if request.user.tenant:
        from farm.models import Farm, FlockBatch, DailyRecord
        from django.db.models import Sum
        
        farms = Farm.objects.filter(tenant=request.user.tenant)
        flocks = FlockBatch.objects.filter(tenant=request.user.tenant, status='ACTIVE')
        total_birds = sum(flock.current_quantity for flock in flocks)
        
        today = timezone.now().date()
        for flock in flocks:
            if flock.bird_type in ['LAYERS', 'KUROILER']:
                today_record = flock.daily_records.filter(date=today).first()
                if today_record:
                    today_eggs += today_record.eggs_collected
        
        if flocks:
            total_initial = sum(flock.initial_quantity for flock in flocks)
            total_mortality = sum(flock.total_mortality for flock in flocks)
            mortality_rate = round((total_mortality / total_initial * 100), 1) if total_initial > 0 else 0
        
        start_of_month = today.replace(day=1)
        monthly_records = DailyRecord.objects.filter(
            tenant=request.user.tenant,
            date__gte=start_of_month,
            date__lte=today
        )
        total_sales = monthly_records.aggregate(total=Sum('sales_revenue'))['total'] or 0
        
    context = {
        'active_nav': 'home',
        'user': request.user,
        'today': timezone.now(),
        'dashboard_type': 'farmer',
        'farms': farms,
        'flocks': flocks,
        'total_birds': total_birds,
        'today_eggs': today_eggs,
        'mortality_rate': mortality_rate,
        'total_sales': total_sales,
    }
    return render(request, 'dashboard/farmer.html', context)


@login_required
def farm_management_view(request):
    """Farm management page - manage farms, houses, flocks"""
    if request.user.role not in ['FARMER', 'ADMIN', 'SUPER_ADMIN']:
        return redirect_role_based_dashboard(request.user)
    
    farms = []
    if request.user.tenant:
        from farm.models import Farm
        farms = Farm.objects.filter(tenant=request.user.tenant)
    
    context = {
        'active_nav': 'farm',
        'user': request.user,
        'farms': farms,
    }
    return render(request, 'farm/dashboard.html', context)


@login_required
def houses_view(request):
    """Houses management page"""
    if request.user.role not in ['FARMER', 'ADMIN', 'SUPER_ADMIN']:
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'farm',
        'user': request.user,
    }
    return render(request, 'farm/houses.html', context)


@login_required
def house_details_view(request, house_id):
    """House details page"""
    if request.user.role not in ['FARMER', 'ADMIN', 'SUPER_ADMIN']:
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'farm',
        'user': request.user,
        'house_id': house_id,
    }
    return render(request, 'farm/house_details.html', context)


@login_required
def flocks_view(request):
    """Flocks list page"""
    if request.user.role not in ['FARMER', 'ADMIN', 'SUPER_ADMIN']:
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'farm',
        'user': request.user,
    }
    return render(request, 'farm/flocks.html', context)


@login_required
def flock_dashboard_view(request, flock_id):
    """Individual flock dashboard"""
    if request.user.role not in ['FARMER', 'ADMIN', 'SUPER_ADMIN']:
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'farm',
        'user': request.user,
        'flock_id': flock_id,
    }
    return render(request, 'farm/flock_dashboard.html', context)


@login_required
def flock_records_view(request, flock_id):
    """Daily records page for a specific flock"""
    if request.user.role not in ['FARMER', 'ADMIN', 'SUPER_ADMIN']:
        return redirect_role_based_dashboard(request.user)
    
    from farm.models import FlockBatch
    try:
        flock = FlockBatch.objects.get(id=flock_id, tenant=request.user.tenant)
    except FlockBatch.DoesNotExist:
        return redirect('frontend:flocks')
    
    context = {
        'active_nav': 'farm',
        'user': request.user,
        'flock_id': flock_id,
    }
    return render(request, 'farm/flock_records.html', context)


@login_required
def vaccinations_view(request, flock_id):
    """Vaccination management page for a specific flock"""
    if request.user.role not in ['FARMER', 'ADMIN', 'SUPER_ADMIN']:
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'farm',
        'user': request.user,
        'flock_id': flock_id,
    }
    return render(request, 'farm/vaccinations.html', context)


@login_required
def health_monitoring_view(request, flock_id):
    """Health monitoring page for a specific flock"""
    if request.user.role not in ['FARMER', 'ADMIN', 'SUPER_ADMIN']:
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'farm',
        'user': request.user,
        'flock_id': flock_id,
    }
    return render(request, 'farm/health_monitoring.html', context)


@login_required
def feed_management_view(request, flock_id):
    """Feed management page for a specific flock"""
    if request.user.role not in ['FARMER', 'ADMIN', 'SUPER_ADMIN']:
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'farm',
        'user': request.user,
        'flock_id': flock_id,
    }
    return render(request, 'farm/feed_management.html', context)

# ==================== CUSTOMER & SHOP VIEWS ====================

@login_required
def customer_dashboard_view(request):
    """Customer dashboard - browse products, shop, track orders"""
    if request.user.role not in ['CUSTOMER', 'ADMIN', 'SUPER_ADMIN']:
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'shop',
        'user': request.user,
        'today': timezone.now(),
        'dashboard_type': 'customer',
    }
    return render(request, 'shop/index.html', context)


@login_required
def shop_view(request):
    """Unified shop view for farmers and customers to browse and purchase products"""
    if request.user.role not in ['FARMER', 'CUSTOMER', 'ADMIN', 'SUPER_ADMIN']:
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'shop',
        'user': request.user,
        'today': timezone.now(),
        'dashboard_type': 'shop',
    }
    return render(request, 'shop/index.html', context)


@login_required
def checkout_view(request):
    """Checkout page for customers to complete purchase"""
    if request.user.role not in ['FARMER', 'CUSTOMER', 'ADMIN', 'SUPER_ADMIN']:
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'shop',
        'user': request.user,
        'today': timezone.now(),
    }
    return render(request, 'shop/checkout.html', context)


@login_required
def order_detail_view(request, order_id):
    """Order detail page for customers to view their order"""
    from marketplace.models import Order
    
    try:
        order = Order.objects.get(id=order_id)
        if request.user.role not in ['ADMIN', 'SUPER_ADMIN'] and order.user != request.user:
            return redirect('frontend:customer_dashboard')
    except Order.DoesNotExist:
        return redirect('frontend:customer_dashboard')
    
    context = {
        'active_nav': 'shop',
        'user': request.user,
        'order': order,
        'today': timezone.now(),
    }
    return render(request, 'shop/order_detail.html', context)

# ==================== SUPPLIER DASHBOARD ====================

@login_required
def supplier_dashboard_view(request):
    """Supplier dashboard - manage products, inventory, orders"""
    if request.user.role not in ['SUPPLIER', 'ADMIN', 'SUPER_ADMIN']:
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'shop',
        'user': request.user,
        'today': timezone.now(),
        'dashboard_type': 'supplier',
    }
    return render(request, 'dashboard/supplier.html', context)

# ==================== TRAINER DASHBOARD ====================

@login_required
def trainer_dashboard_view(request):
    """Trainer dashboard - manage courses, students"""
    if request.user.role not in ['TRAINER', 'ADMIN', 'SUPER_ADMIN']:
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'learn',
        'user': request.user,
        'today': timezone.now(),
        'dashboard_type': 'trainer',
    }
    return render(request, 'dashboard/trainer.html', context)

# ==================== FIELD OFFICER DASHBOARD ====================

@login_required
def field_officer_dashboard_view(request):
    """Field Officer dashboard - Vet/Extension Worker"""
    if request.user.role not in ['FIELD_OFFICER', 'ADMIN', 'SUPER_ADMIN']:
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'field_officer',
        'user': request.user,
        'today': timezone.now(),
        'dashboard_type': 'field_officer',
    }
    return render(request, 'dashboard/field_officer.html', context)

# ==================== ORGANIZATION DASHBOARDS ====================

@login_required
def organization_default_dashboard_view(request):
    """Default organization dashboard for other types"""
    if request.user.role != 'ORGANIZATION':
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'organization',
        'user': request.user,
        'today': timezone.now(),
        'dashboard_type': 'organization',
        'org_type': request.user.organization_type or 'OTHER',
    }
    return render(request, 'dashboard/organizations/default.html', context)


@login_required
def cooperative_dashboard_view(request):
    """Cooperative dashboard - Focus on member farmers and collective selling"""
    if request.user.role != 'ORGANIZATION' or request.user.organization_type != 'COOPERATIVE':
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'cooperative',
        'user': request.user,
        'today': timezone.now(),
        'dashboard_type': 'cooperative',
        'org_type': 'COOPERATIVE',
    }
    return render(request, 'dashboard/organizations/cooperative.html', context)


@login_required
def ngo_dashboard_view(request):
    """NGO dashboard - Focus on outreach, training, and impact tracking"""
    if request.user.role != 'ORGANIZATION' or request.user.organization_type != 'NGO':
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'ngo',
        'user': request.user,
        'today': timezone.now(),
        'dashboard_type': 'ngo',
        'org_type': 'NGO',
    }
    return render(request, 'dashboard/organizations/ngo.html', context)


@login_required
def government_dashboard_view(request):
    """Government dashboard - Focus on policy, compliance, and regional statistics"""
    if request.user.role != 'ORGANIZATION' or request.user.organization_type != 'GOVERNMENT':
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'government',
        'user': request.user,
        'today': timezone.now(),
        'dashboard_type': 'government',
        'org_type': 'GOVERNMENT',
    }
    return render(request, 'dashboard/organizations/government.html', context)


@login_required
def research_dashboard_view(request):
    """Research dashboard - Focus on data collection, studies, and publications"""
    if request.user.role != 'ORGANIZATION' or request.user.organization_type != 'RESEARCH':
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'research',
        'user': request.user,
        'today': timezone.now(),
        'dashboard_type': 'research',
        'org_type': 'RESEARCH',
    }
    return render(request, 'dashboard/organizations/research.html', context)


# ==================== AGRIBUSINESS MANAGEMENT VIEWS (MODULAR) ====================

@login_required
def agribusiness_dashboard_view(request):
    """Agribusiness dashboard - main overview (Modular)"""
    if request.user.role != 'ORGANIZATION' or request.user.organization_type != 'AGRIBUSINESS':
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'dashboard',
        'user': request.user,
        'today': timezone.now(),
    }
    return render(request, 'agribusiness/dashboard.html', context)


@login_required
def agribusiness_products_view(request):
    """Agribusiness products management"""
    if request.user.role != 'ORGANIZATION' or request.user.organization_type != 'AGRIBUSINESS':
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'products',
        'user': request.user,
    }
    return render(request, 'agribusiness/products.html', context)


@login_required
def agribusiness_add_product_view(request):
    """Agribusiness add product page"""
    if request.user.role != 'ORGANIZATION' or request.user.organization_type != 'AGRIBUSINESS':
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'products',
        'user': request.user,
    }
    return render(request, 'agribusiness/add_product.html', context)


@login_required
def agribusiness_edit_product_view(request, product_id):
    """Agribusiness edit product page"""
    if request.user.role != 'ORGANIZATION' or request.user.organization_type != 'AGRIBUSINESS':
        return redirect_role_based_dashboard(request.user)
    
    from marketplace.models import Product
    
    try:
        product = Product.objects.get(id=product_id, tenant=request.user.tenant)
    except Product.DoesNotExist:
        return redirect('frontend:agribusiness_products')
    
    context = {
        'active_nav': 'products',
        'user': request.user,
        'product': product,
        'product_id': product_id,
    }
    return render(request, 'agribusiness/edit_product.html', context)


@login_required
def agribusiness_orders_view(request):
    """Agribusiness orders management"""
    if request.user.role != 'ORGANIZATION' or request.user.organization_type != 'AGRIBUSINESS':
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'orders',
        'user': request.user,
    }
    return render(request, 'agribusiness/orders.html', context)


# frontend/views.py - Make sure this exists

@login_required
def agribusiness_order_detail_view(request, order_id):
    """Agribusiness order detail page"""
    if request.user.role != 'ORGANIZATION' or request.user.organization_type != 'AGRIBUSINESS':
        return redirect_role_based_dashboard(request.user)
    
    from marketplace.models import Order
    
    try:
        order = Order.objects.get(id=order_id, tenant=request.user.tenant)
    except Order.DoesNotExist:
        return redirect('frontend:agribusiness_orders')
    
    context = {
        'active_nav': 'orders',
        'user': request.user,
        'order': order,
        'order_id': order_id,
    }
    return render(request, 'agribusiness/order_detail.html', context)


@login_required
def agribusiness_inventory_view(request):
    """Agribusiness inventory management"""
    if request.user.role != 'ORGANIZATION' or request.user.organization_type != 'AGRIBUSINESS':
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'inventory',
        'user': request.user,
    }
    return render(request, 'agribusiness/inventory.html', context)


@login_required
def agribusiness_price_list_view(request):
    """Agribusiness price list management"""
    if request.user.role != 'ORGANIZATION' or request.user.organization_type != 'AGRIBUSINESS':
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'price_list',
        'user': request.user,
    }
    return render(request, 'agribusiness/price_list.html', context)

# ==================== ADMIN DASHBOARD ====================

@login_required
def admin_dashboard_view(request):
    """Admin dashboard - manage platform"""
    if request.user.role not in ['ADMIN', 'SUPER_ADMIN']:
        return redirect_role_based_dashboard(request.user)
    
    context = {
        'active_nav': 'dashboard',
        'user': request.user,
        'today': timezone.now(),
        'dashboard_type': 'admin',
    }
    return render(request, 'dashboard/admin.html', context)

# ==================== PROFILE VIEW ====================

@login_required
def profile_view(request):
    """User profile page - works for all roles"""
    if request.user.created_at:
        member_days = (timezone.now() - request.user.created_at).days
    else:
        member_days = 1
    
    context = {
        'active_nav': 'profile',
        'user': request.user,
        'member_days': member_days,
        'total_flocks': 0,
        'certificates': 0,
        'dashboard_type': request.user.role.lower(),
    }
    return render(request, 'profile/index.html', context)

# ==================== MARKETPLACE AND COURSES ALIASES ====================

@login_required
def marketplace_view(request):
    """Marketplace - redirect to customer dashboard"""
    return redirect('frontend:customer_dashboard')


@login_required
def courses_view(request):
    """Courses - redirect to trainer dashboard"""
    return redirect('frontend:trainer_dashboard')

# ==================== LOGOUT VIEWS ====================

@require_http_methods(["POST"])
def logout_view(request):
    """Handle logout via POST request"""
    if request.user.is_authenticated:
        auth_logout(request)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': True, 'message': 'Logged out successfully'})
        return redirect('frontend:login')
    return redirect('frontend:login')


def logout_get_view(request):
    """GET logout - only for development"""
    if request.user.is_authenticated:
        auth_logout(request)
    return redirect('frontend:login')