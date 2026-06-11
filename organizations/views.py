# organizations/views.py
import logging
from decimal import Decimal
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import timedelta
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status

from accounts.models import User
from farm.models import FlockBatch, DailyRecord, FeedPurchase, FeedType, Farm
from marketplace.models import Order
from tenants.models import Tenant

logger = logging.getLogger(__name__)


class OrganizationDashboardStatsView(APIView):
    """Get dashboard statistics for organization"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            tenant = request.user.tenant
            if not tenant:
                return Response({
                    'success': False,
                    'message': 'No organization associated with this account'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get farmers under this organization (users with role FARMER)
            farmers = User.objects.filter(tenant=tenant, role='FARMER', is_active=True)
            total_farmers = farmers.count()
            
            # Get farms owned by these farmers
            farms = Farm.objects.filter(tenant=tenant, created_by__in=farmers)
            
            # Get flocks through farms (since FlockBatch has farm, not direct farmer)
            flocks = FlockBatch.objects.filter(tenant=tenant, farm__in=farms)
            total_flocks = flocks.count()
            active_flocks = flocks.filter(status='ACTIVE').count()
            total_birds = flocks.aggregate(total=Sum('current_quantity'))['total'] or 0
            
            # Get daily records for financials
            daily_records = DailyRecord.objects.filter(tenant=tenant)
            total_revenue = daily_records.aggregate(total=Sum('sales_revenue'))['total'] or Decimal('0')
            total_expenses = daily_records.aggregate(total=Sum('total_expenses'))['total'] or Decimal('0')
            
            # Get orders revenue
            orders_revenue = Order.objects.filter(
                tenant=tenant, 
                status='DELIVERED'
            ).aggregate(total=Sum('total'))['total'] or Decimal('0')
            
            total_revenue += orders_revenue
            
            # Calculate mortality
            total_mortality = 0
            for flock in flocks:
                total_mortality += (flock.initial_quantity - (flock.current_quantity or 0))
            
            return Response({
                'success': True,
                'stats': {
                    'total_farmers': total_farmers,
                    'total_flocks': total_flocks,
                    'active_flocks': active_flocks,
                    'total_birds': total_birds,
                    'total_revenue': float(total_revenue),
                    'total_expenses': float(total_expenses),
                    'net_profit': float(total_revenue - total_expenses),
                    'total_mortality': total_mortality
                }
            })
            
        except Exception as e:
            logger.error(f"Error fetching dashboard stats: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrganizationFarmersView(APIView):
    """Get all farmers under this organization"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            tenant = request.user.tenant
            if not tenant:
                return Response({
                    'success': False,
                    'message': 'No organization associated'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get all farmers (users with role FARMER)
            farmers = User.objects.filter(tenant=tenant, role='FARMER', is_active=True)
            
            farmers_data = []
            for farmer in farmers:
                # Get farmer's farms
                farms = Farm.objects.filter(tenant=tenant, created_by=farmer)
                farm_ids = farms.values_list('id', flat=True)
                
                if farm_ids:
                    # Get flocks through farms - use QuerySet
                    flocks = FlockBatch.objects.filter(tenant=tenant, farm_id__in=farm_ids)
                    total_flocks = flocks.count()
                    total_birds = flocks.aggregate(total=Sum('current_quantity'))['total'] or 0
                    
                    # Get daily records through flocks
                    batch_ids = flocks.values_list('id', flat=True)
                    daily_records = DailyRecord.objects.filter(tenant=tenant, batch_id__in=batch_ids)
                    total_spent = daily_records.aggregate(total=Sum('total_expenses'))['total'] or Decimal('0')
                    total_earned = daily_records.aggregate(total=Sum('sales_revenue'))['total'] or Decimal('0')
                else:
                    total_flocks = 0
                    total_birds = 0
                    total_spent = Decimal('0')
                    total_earned = Decimal('0')
                
                farmers_data.append({
                    'id': farmer.id,
                    'full_name': farmer.full_name,
                    'phone_number': farmer.phone_number,
                    'email': getattr(farmer, 'email', ''),
                    'total_flocks': total_flocks,
                    'total_birds': total_birds,
                    'total_spent': float(total_spent),
                    'total_earned': float(total_earned),
                    'is_active': farmer.is_active,
                    'registered_date': farmer.created_at.strftime('%Y-%m-%d'),
                    'district': getattr(farmer.profile, 'district', 'N/A') if hasattr(farmer, 'profile') else 'N/A'
                })
            
            return Response({
                'success': True,
                'farmers': farmers_data,
                'total': len(farmers_data)
            })
            
        except Exception as e:
            logger.error(f"Error fetching farmers: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# organizations/views.py - Update OrganizationFlocksView

class OrganizationFlocksView(APIView):
    """Get all flocks under this organization"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            tenant = request.user.tenant
            
            # REMOVE any status filter - get ALL flocks
            flocks = FlockBatch.objects.filter(tenant=tenant).select_related('farm', 'farm__created_by', 'house')
            
            # DON'T filter by status here
            # flocks = flocks.filter(status='ACTIVE')  # <-- REMOVE THIS IF EXISTS
            
            print(f"DEBUG: Total flocks found (all statuses): {flocks.count()}")
            print(f"DEBUG: Planned flocks: {flocks.filter(status='PLANNED').count()}")
            print(f"DEBUG: Active flocks: {flocks.filter(status='ACTIVE').count()}")
            
            status_map = {
                'PLANNED': {'display': 'Planned', 'color': 'warning'},
                'ACTIVE': {'display': 'Active', 'color': 'success'},
                'COMPLETED': {'display': 'Completed', 'color': 'info'},
                'CULLED': {'display': 'Culled', 'color': 'danger'},
                'DEPLETED': {'display': 'Depleted', 'color': 'secondary'},
                'SICK': {'display': 'Sick', 'color': 'danger'},
            }
            
            bird_type_map = {
                'LAYERS': '🥚 Layers',
                'BROILERS': '🍗 Broilers',
                'DAY_OLD': '🐣 Day Old Chicks',
                'GROWERS': '🐔 Growers',
                'BREEDERS': '🐓 Breeders',
                'KUROILER': '🐔 Kuroiler',
                'POINTS': '🥚 Point of Lay',
            }
            
            flocks_data = []
            for flock in flocks:
                mortality = (flock.initial_quantity - (flock.current_quantity or 0))
                mortality_rate = (mortality / flock.initial_quantity * 100) if flock.initial_quantity > 0 else 0
                
                # Get farmer name from farm.created_by
                farmer_name = 'N/A'
                farmer_id = None
                farm_name = 'N/A'
                
                if flock.farm:
                    farm_name = flock.farm.farm_name
                    if flock.farm.created_by:
                        farmer_name = flock.farm.created_by.full_name
                        farmer_id = flock.farm.created_by.id
                
                flocks_data.append({
                    'id': flock.id,
                    'farmer_id': farmer_id,
                    'farmer_name': farmer_name,
                    'farm_name': farm_name,
                    'batch_name': flock.batch_name,
                    'batch_number': flock.batch_number,
                    'bird_type': bird_type_map.get(flock.bird_type, flock.bird_type),
                    'bird_type_raw': flock.bird_type,
                    'breed': flock.get_breed_display(),
                    'status': flock.status,
                    'status_display': status_map.get(flock.status, {}).get('display', flock.status),
                    'status_color': status_map.get(flock.status, {}).get('color', 'secondary'),
                    'initial_quantity': flock.initial_quantity,
                    'current_quantity': flock.current_quantity or 0,
                    'mortality': mortality,
                    'mortality_rate': round(mortality_rate, 1),
                    'age_weeks': flock.age_weeks,
                    'age_days': flock.age_days,
                    'start_date': flock.start_date.strftime('%Y-%m-%d'),
                    'expected_end_date': flock.expected_end_date.strftime('%Y-%m-%d') if flock.expected_end_date else 'N/A',
                    'total_feed_consumed': float(flock.total_feed_consumed),
                    'total_eggs_produced': flock.total_eggs_produced,
                    'notes': flock.notes[:100] if flock.notes else ''
                })
            
            # Calculate stage counts for all statuses
            stage_counts = {
                'planned': flocks.filter(status='PLANNED').count(),
                'active': flocks.filter(status='ACTIVE').count(),
                'completed': flocks.filter(status='COMPLETED').count(),
                'sick': flocks.filter(status='SICK').count(),
                'culled': flocks.filter(status='CULLED').count(),
                'depleted': flocks.filter(status='DEPLETED').count()
            }
            
            return Response({
                'success': True,
                'flocks': flocks_data,
                'stage_counts': stage_counts,
                'total': len(flocks_data)
            })
            
        except Exception as e:
            logger.error(f"Error fetching flocks: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrganizationDailyRecordsView(APIView):
    """Get daily records for expenses and incomes"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            tenant = request.user.tenant
            
            # Get all farmers under this organization
            farmers = User.objects.filter(tenant=tenant, role='FARMER', is_active=True)
            
            # Get farms for these farmers
            farms = Farm.objects.filter(tenant=tenant, created_by__in=farmers)
            
            # Get flocks through farms
            flocks = FlockBatch.objects.filter(tenant=tenant, farm__in=farms)
            batch_ids = [flock.id for flock in flocks]
            
            # Get daily records for these batches
            records = DailyRecord.objects.filter(
                tenant=tenant,
                batch_id__in=batch_ids
            ).select_related('batch', 'batch__farm', 'batch__farm__created_by').order_by('-date')
            
            records_data = []
            for record in records:
                records_data.append({
                    'id': record.id,
                    'date': record.date.strftime('%Y-%m-%d'),
                    'farmer_id': record.batch.farm.created_by.id if record.batch and record.batch.farm and record.batch.farm.created_by else None,
                    'farmer_name': record.batch.farm.created_by.full_name if record.batch and record.batch.farm and record.batch.farm.created_by else 'N/A',
                    'batch_id': record.batch.id if record.batch else None,
                    'batch_name': record.batch.batch_name if record.batch else 'N/A',
                    # Bird counts
                    'opening_bird_count': record.opening_bird_count,
                    'mortality': record.mortality,
                    'birds_sold': record.birds_sold_count,
                    'closing_bird_count': record.closing_bird_count,
                    # Feed
                    'feed_type': record.get_feed_type_display() if record.feed_type else 'N/A',
                    'feed_given_kg': float(record.feed_given_kg),
                    'feed_consumed_kg': float(record.feed_consumed_kg),
                    # Health
                    'health_status': record.get_health_status_display(),
                    'health_status_raw': record.health_status,
                    # Layer production
                    'eggs_collected': record.eggs_collected,
                    'eggs_saleable': record.eggs_saleable,
                    'egg_production_percent': float(record.egg_production_percent) if record.egg_production_percent else 0,
                    # Sales
                    'birds_sold_count': record.birds_sold_count,
                    'eggs_sold_count': record.eggs_sold_count,
                    'price_per_bird': float(record.price_per_bird),
                    'price_per_egg': float(record.price_per_egg),
                    'sales_revenue': float(record.sales_revenue),
                    # Expenses
                    'feed_cost': float(record.feed_cost),
                    'medication_cost': float(record.medication_cost),
                    'vaccine_cost': float(record.vaccine_cost),
                    'labour_cost': float(record.labour_cost),
                    'transport_cost': float(record.transport_cost),
                    'utilities_cost': float(record.utilities_cost),
                    'other_cost': float(record.other_cost),
                    'total_expenses': float(record.total_expenses),
                    # Notes
                    'farmer_observations': record.farmer_observations[:200] if record.farmer_observations else '',
                    'alerts': record.alerts_generated
                })
            
            # Calculate totals
            total_revenue = sum(r['sales_revenue'] for r in records_data)
            total_expenses = sum(r['total_expenses'] for r in records_data)
            
            return Response({
                'success': True,
                'records': records_data,
                'totals': {
                    'revenue': total_revenue,
                    'expenses': total_expenses,
                    'profit': total_revenue - total_expenses
                },
                'total_records': len(records_data)
            })
            
        except Exception as e:
            logger.error(f"Error fetching daily records: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrganizationFeedPurchasesView(APIView):
    """Get feed purchases under this organization"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            tenant = request.user.tenant
            
            purchases = FeedPurchase.objects.filter(
                tenant=tenant
            ).select_related('feed_type', 'inventory').order_by('-purchase_date')
            
            purchases_data = []
            for purchase in purchases:
                purchases_data.append({
                    'id': purchase.id,
                    'purchase_date': purchase.purchase_date.strftime('%Y-%m-%d'),
                    'feed_type': purchase.feed_type.name if purchase.feed_type else 'N/A',
                    'feed_type_id': purchase.feed_type.id if purchase.feed_type else None,
                    'quantity_kg': float(purchase.quantity_kg),
                    'cost_per_kg': float(purchase.cost_per_kg),
                    'total_cost': float(purchase.total_cost),
                    'invoice_number': purchase.invoice_number,
                    'supplier_name': purchase.supplier_name,
                    'supplier_contact': purchase.supplier_contact,
                    'payment_status': purchase.payment_status,
                    'delivery_date': purchase.delivery_date.strftime('%Y-%m-%d') if purchase.delivery_date else 'Pending',
                    'notes': purchase.notes[:100] if purchase.notes else ''
                })
            
            # Calculate totals
            total_quantity = sum(p['quantity_kg'] for p in purchases_data)
            total_cost = sum(p['total_cost'] for p in purchases_data)
            
            return Response({
                'success': True,
                'purchases': purchases_data,
                'totals': {
                    'total_quantity_kg': total_quantity,
                    'total_cost': total_cost,
                    'average_cost_per_kg': total_cost / total_quantity if total_quantity > 0 else 0
                }
            })
            
        except Exception as e:
            logger.error(f"Error fetching feed purchases: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrganizationOrdersView(APIView):
    """Get marketplace orders under this organization"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        try:
            tenant = request.user.tenant
            
            orders = Order.objects.filter(
                tenant=tenant
            ).select_related('user').order_by('-created_at')
            
            orders_data = []
            for order in orders:
                orders_data.append({
                    'id': order.id,
                    'order_number': order.order_number,
                    'created_at': order.created_at.strftime('%Y-%m-%d %H:%M'),
                    'customer_name': order.user.full_name if order.user else 'Anonymous',
                    'customer_phone': order.user.phone_number if order.user else 'N/A',
                    'farmer_name': 'N/A',
                    'farmer_id': None,
                    'items_count': order.items.count() if hasattr(order, 'items') else 0,
                    'subtotal': float(order.subtotal) if order.subtotal else 0,
                    'tax': float(order.tax) if order.tax else 0,
                    'shipping_cost': float(order.shipping_cost) if order.shipping_cost else 0,
                    'total': float(order.total) if order.total else 0,
                    'status': order.status,
                    'payment_status': order.payment_status,
                    'payment_method': order.payment_method,
                    'shipping_address': order.shipping_address[:100] if order.shipping_address else 'N/A',
                    'customer_notes': order.customer_notes[:100] if order.customer_notes else ''
                })
            
            # Status counts
            status_counts = {}
            for order in orders:
                status_counts[order.status] = status_counts.get(order.status, 0) + 1
            
            return Response({
                'success': True,
                'orders': orders_data,
                'status_counts': status_counts,
                'total': len(orders_data)
            })
            
        except Exception as e:
            logger.error(f"Error fetching orders: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def put(self, request, order_id):
        try:
            tenant = request.user.tenant
            order = Order.objects.get(id=order_id, tenant=tenant)
            
            new_status = request.data.get('status')
            if new_status:
                order.status = new_status
                order.save()
            
            return Response({
                'success': True,
                'message': f'Order status updated to {new_status}'
            })
            
        except Order.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Order not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class OrganizationFarmerDetailView(APIView):
    """Get detailed information for a specific farmer"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, farmer_id):
        try:
            tenant = request.user.tenant
            farmer = User.objects.get(id=farmer_id, tenant=tenant, role='FARMER')
            
            # Get profile data
            profile = None
            if hasattr(farmer, 'profile'):
                profile = farmer.profile
            
            # Get farmer's farms
            farms = Farm.objects.filter(tenant=tenant, created_by=farmer)
            farm_ids = [f.id for f in farms]
            
            # Get flocks through farms
            flocks = FlockBatch.objects.filter(tenant=tenant, farm_id__in=farm_ids)
            
            flocks_data = []
            for flock in flocks:
                flocks_data.append({
                    'id': flock.id,
                    'batch_name': flock.batch_name,
                    'bird_type': flock.get_bird_type_display(),
                    'status': flock.status,
                    'initial_quantity': flock.initial_quantity,
                    'current_quantity': flock.current_quantity,
                    'age_weeks': flock.age_weeks,
                    'start_date': flock.start_date.strftime('%Y-%m-%d'),
                    'total_eggs': flock.total_eggs_produced,
                    'total_feed': float(flock.total_feed_consumed)
                })
            
            # Get daily records through flocks
            batch_ids = [f.id for f in flocks]
            daily_records = DailyRecord.objects.filter(
                tenant=tenant, 
                batch_id__in=batch_ids
            ).order_by('-date')[:30]
            
            records_data = []
            for record in daily_records:
                records_data.append({
                    'date': record.date.strftime('%Y-%m-%d'),
                    'sales_revenue': float(record.sales_revenue),
                    'total_expenses': float(record.total_expenses),
                    'mortality': record.mortality,
                    'eggs_collected': record.eggs_collected
                })
            
            # Calculate totals
            total_revenue = sum(r['sales_revenue'] for r in records_data)
            total_expenses = sum(r['total_expenses'] for r in records_data)
            
            return Response({
                'success': True,
                'farmer': {
                    'id': farmer.id,
                    'full_name': farmer.full_name,
                    'phone_number': farmer.phone_number,
                    'email': getattr(farmer, 'email', ''),
                    'registered_date': farmer.created_at.strftime('%Y-%m-%d'),
                    'is_active': farmer.is_active,
                    # Get district and village from profile
                    'district': profile.district if profile else 'Not specified',
                    'village': profile.village if profile else 'Not specified',
                },
                'flocks': flocks_data,
                'recent_records': records_data,
                'financial_summary': {
                    'total_revenue': float(total_revenue),
                    'total_expenses': float(total_expenses),
                    'net_profit': float(total_revenue - total_expenses)
                }
            })
            
        except User.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Farmer not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching farmer details: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# organizations/views.py - Add this new class

class OrganizationFlockDetailView(APIView):
    """Get detailed information for a specific flock"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, flock_id):
        try:
            tenant = request.user.tenant
            flock = FlockBatch.objects.get(id=flock_id, tenant=tenant)
            
            # Get farmer info through farm
            farmer_name = 'N/A'
            farmer_id = None
            farm_name = 'N/A'
            
            if flock.farm:
                farm_name = flock.farm.farm_name
                if flock.farm.created_by:
                    farmer_name = flock.farm.created_by.full_name
                    farmer_id = flock.farm.created_by.id
            
            # Get daily records for this flock
            daily_records = DailyRecord.objects.filter(
                batch=flock,
                tenant=tenant
            ).order_by('-date')[:30]
            
            records_data = []
            for record in daily_records:
                records_data.append({
                    'id': record.id,
                    'date': record.date.strftime('%Y-%m-%d'),
                    'opening_bird_count': record.opening_bird_count,
                    'mortality': record.mortality,
                    'birds_sold': record.birds_sold_count,
                    'closing_bird_count': record.closing_bird_count,
                    'feed_consumed_kg': float(record.feed_consumed_kg),
                    'eggs_collected': record.eggs_collected,
                    'eggs_sold': record.eggs_sold_count,
                    'sales_revenue': float(record.sales_revenue),
                    'feed_cost': float(record.feed_cost),
                    'medication_cost': float(record.medication_cost),
                    'labour_cost': float(record.labour_cost),
                    'total_expenses': float(record.total_expenses),
                    'health_status': record.get_health_status_display(),
                    'farmer_observations': record.farmer_observations[:200] if record.farmer_observations else ''
                })
            
            # Calculate summary statistics
            total_mortality = sum(r['mortality'] for r in records_data)
            total_feed_consumed = sum(r['feed_consumed_kg'] for r in records_data)
            total_eggs = sum(r['eggs_collected'] for r in records_data)
            total_revenue = sum(r['sales_revenue'] for r in records_data)
            total_expenses = sum(r['total_expenses'] for r in records_data)
            
            # Get health records
            health_records = flock.health_records.all().order_by('-record_date')[:10]
            health_data = []
            for hr in health_records:
                health_data.append({
                    'date': hr.record_date.strftime('%Y-%m-%d'),
                    'health_status': hr.get_health_status_display(),
                    'disease_type': hr.get_disease_type_display() if hr.disease_type else 'N/A',
                    'affected_birds': hr.affected_birds_count,
                    'symptoms': hr.symptoms[:100] if hr.symptoms else '',
                    'observations': hr.observations[:100] if hr.observations else ''
                })
            
            # Get vaccination records
            vaccinations = flock.vaccinations.all().order_by('-scheduled_date')[:10]
            vaccination_data = []
            for vac in vaccinations:
                vaccination_data.append({
                    'vaccine_type': vac.get_vaccine_type_display(),
                    'scheduled_date': vac.scheduled_date.strftime('%Y-%m-%d'),
                    'administered_date': vac.administered_date.strftime('%Y-%m-%d') if vac.administered_date else 'Pending',
                    'status': vac.status,
                    'administered_by': vac.administered_by or 'N/A'
                })
            
            return Response({
                'success': True,
                'flock': {
                    'id': flock.id,
                    'batch_name': flock.batch_name,
                    'batch_number': flock.batch_number,
                    'bird_type': flock.get_bird_type_display(),
                    'breed': flock.get_breed_display(),
                    'status': flock.status,
                    'status_display': flock.get_status_display(),
                    'initial_quantity': flock.initial_quantity,
                    'current_quantity': flock.current_quantity,
                    'mortality_rate': round(flock.mortality_rate, 1),
                    'survival_rate': round(flock.survival_rate, 1),
                    'age_days': flock.age_days,
                    'age_weeks': flock.age_weeks,
                    'start_date': flock.start_date.strftime('%Y-%m-%d'),
                    'expected_end_date': flock.expected_end_date.strftime('%Y-%m-%d') if flock.expected_end_date else 'N/A',
                    'source': flock.source or 'N/A',
                    'cost_per_bird': float(flock.cost_per_bird),
                    'total_cost': float(flock.total_cost),
                    'farmer_id': farmer_id,
                    'farmer_name': farmer_name,
                    'farm_name': farm_name,
                    'notes': flock.notes,
                    'total_feed_consumed': float(flock.total_feed_consumed),
                    'total_eggs_produced': flock.total_eggs_produced,
                    'avg_daily_eggs': round(flock.avg_daily_eggs, 1),
                    'feed_conversion_ratio': round(flock.feed_conversion_ratio, 2)
                },
                'daily_records': records_data,
                'health_records': health_data,
                'vaccination_records': vaccination_data,
                'summary': {
                    'total_mortality': total_mortality,
                    'total_feed_consumed_kg': round(total_feed_consumed, 2),
                    'total_eggs_produced': total_eggs,
                    'total_revenue': round(total_revenue, 2),
                    'total_expenses': round(total_expenses, 2),
                    'net_profit': round(total_revenue - total_expenses, 2)
                }
            })
            
        except FlockBatch.DoesNotExist:
            return Response({
                'success': False,
                'message': 'Flock not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching flock details: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)