from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser,IsAuthenticated
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta
from farm.models import Farm, FlockBatch, DailyRecord
from accounts.models import User

class FarmerDashboardAnalyticsView(APIView):
    """Analytics data for farmer dashboard"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        # Ensure user is authenticated
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=401)
        
        user = request.user
        tenant = user.tenant
        
        if not tenant:
            return Response({
                'total_birds': 0,
                'total_eggs': 0,
                'mortality_rate': 0,
                'total_sales': 0,
                'active_flocks': 0,
                'feed_stock': 0,
                'growth_percent': 0,
                'production_rate': 0,
                'this_month_sales': 0,
                'recent_alerts': []
            })
        
        # Get active flocks
        active_flocks = FlockBatch.objects.filter(tenant=tenant, status='ACTIVE')
        
        # Calculate total birds
        total_birds = active_flocks.aggregate(total=Sum('current_quantity'))['total'] or 0
        
        # Calculate today's eggs
        today = timezone.now().date()
        today_records = DailyRecord.objects.filter(
            tenant=tenant,
            date=today,
            batch__bird_type__in=['LAYERS', 'KUROILER']
        )
        total_eggs = today_records.aggregate(total=Sum('eggs_collected'))['total'] or 0
        
        # Calculate mortality rate
        total_initial = active_flocks.aggregate(total=Sum('initial_quantity'))['total'] or 1
        total_mortality = 0
        for flock in active_flocks:
            total_mortality += flock.total_mortality
        mortality_rate = (total_mortality / total_initial * 100) if total_initial > 0 else 0
        
        # Calculate this month's sales from daily records
        start_of_month = today.replace(day=1)
        monthly_records = DailyRecord.objects.filter(
            tenant=tenant,
            date__gte=start_of_month,
            date__lte=today
        )
        monthly_sales = monthly_records.aggregate(total=Sum('sales_revenue'))['total'] or 0
        
        # Calculate growth percentage
        last_month_start = (start_of_month - timedelta(days=1)).replace(day=1)
        last_month_end = start_of_month - timedelta(days=1)
        last_month_records = DailyRecord.objects.filter(
            tenant=tenant,
            date__gte=last_month_start,
            date__lte=last_month_end
        )
        last_month_sales = last_month_records.aggregate(total=Sum('sales_revenue'))['total'] or 0
        
        if last_month_sales > 0:
            growth_percent = ((monthly_sales - last_month_sales) / last_month_sales) * 100
        else:
            growth_percent = 100 if monthly_sales > 0 else 0
        
        # Calculate production rate
        production_rate = (total_eggs / total_birds * 100) if total_birds > 0 else 0
        
        # Get recent alerts
        recent_alerts = []
        alert_records = DailyRecord.objects.filter(
            tenant=tenant,
            date__gte=today - timedelta(days=7)
        ).exclude(alerts_generated=[]).order_by('-date')[:5]
        
        for record in alert_records:
            if record.alerts_generated:
                for alert in record.alerts_generated:
                    recent_alerts.append({
                        'date': record.date.strftime('%Y-%m-%d'),
                        'message': alert.get('message', ''),
                        'type': alert.get('type', 'INFO'),
                        'severity': alert.get('severity', 'MEDIUM')
                    })
        
        return Response({
            'total_birds': total_birds,
            'total_eggs': total_eggs,
            'mortality_rate': round(mortality_rate, 1),
            'total_sales': monthly_sales,
            'active_flocks': active_flocks.count(),
            'feed_stock': 0,
            'growth_percent': round(growth_percent, 1),
            'production_rate': round(production_rate, 1),
            'this_month_sales': monthly_sales,
            'recent_alerts': recent_alerts[:5]
        })


# analytics/views.py - Update FarmerFlocksAnalyticsView

class FarmerFlocksAnalyticsView(APIView):
    """Get flocks data for farmer dashboard"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_authenticated:
            return Response([])  # Return empty array instead of error
        
        tenant = request.user.tenant
        
        if not tenant:
            return Response([])  # Return empty array
        
        flocks = FlockBatch.objects.filter(tenant=tenant, status='ACTIVE')
        
        data = []
        for flock in flocks:
            data.append({
                'id': flock.id,
                'batch_name': flock.batch_name,
                'bird_type': flock.bird_type,
                'breed': flock.breed,
                'quantity': flock.current_quantity,
                'age_days': flock.age_days,
                'mortality_rate': round(flock.mortality_rate, 1),
                'progress_percent': flock.progress_percent,
                'avg_daily_eggs': flock.avg_daily_eggs,
                'expected_harvest_date': flock.expected_end_date.strftime('%Y-%m-%d') if flock.expected_end_date else None
            })
        
        return Response(data)  # Always return an array


class DashboardStatsView(APIView):
    """Main dashboard statistics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=401)
        
        user = request.user
        tenant = user.tenant
        
        if user.role == 'SUPER_ADMIN':
            from tenants.models import Tenant
            total_users = User.objects.count()
            total_tenants = Tenant.objects.count()
            total_farms = Farm.objects.count()
            total_flocks = FlockBatch.objects.count()
            
            return Response({
                'total_users': total_users,
                'total_tenants': total_tenants,
                'total_farms': total_farms,
                'total_flocks': total_flocks,
                'revenue': 0
            })
        
        elif tenant:
            total_farms = Farm.objects.filter(tenant=tenant).count()
            active_flocks = FlockBatch.objects.filter(tenant=tenant, status='ACTIVE').count()
            total_birds = FlockBatch.objects.filter(tenant=tenant, status='ACTIVE').aggregate(
                total=Sum('current_quantity')
            )['total'] or 0
            
            return Response({
                'total_farms': total_farms,
                'active_flocks': active_flocks,
                'total_birds': total_birds
            })
        
        return Response({
            'total_farms': 0,
            'active_flocks': 0,
            'total_birds': 0
        })

class AdminDashboardStatsView(APIView):
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        from accounts.models import User
        from tenants.models import Tenant
        from farm.models import FlockBatch
        from marketplace.models import Order
        from courses.models import Course, Enrollment
        
        # User stats
        total_users = User.objects.count()
        active_farmers = User.objects.filter(role='FARMER', is_active=True).count()
        
        # Tenant stats
        total_tenants = Tenant.objects.count()
        active_tenants = Tenant.objects.filter(is_active=True).count()
        
        # Farm stats
        total_flocks = FlockBatch.objects.filter(status='ACTIVE').count()
        
        # Sales stats (last 30 days)
        thirty_days_ago = timezone.now() - timedelta(days=30)
        recent_orders = Order.objects.filter(created_at__gte=thirty_days_ago)
        total_revenue = recent_orders.aggregate(total=Sum('total_amount'))['total'] or 0
        total_commission = recent_orders.aggregate(total=Sum('platform_commission'))['total'] or 0
        
        # Course stats
        total_courses = Course.objects.filter(is_published=True).count()
        total_enrollments = Enrollment.objects.count()
        
        return Response({
            'users': {
                'total': total_users,
                'active_farmers': active_farmers,
                'growth_percent': 12.5,  # Calculate from previous period
            },
            'tenants': {
                'total': total_tenants,
                'active': active_tenants,
            },
            'farming': {
                'active_flocks': total_flocks,
            },
            'revenue': {
                'last_30_days': total_revenue,
                'commission': total_commission,
                'currency': 'UGX',
            },
            'learning': {
                'total_courses': total_courses,
                'total_enrollments': total_enrollments,
            }
        })