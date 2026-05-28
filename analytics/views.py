from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db.models import Count, Sum, Avg
from django.utils import timezone
from datetime import timedelta

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