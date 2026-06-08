# farm/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.authentication import SessionAuthentication, BasicAuthentication
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view
from django.db.models import Sum, Avg
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta, date as date_type
from django.shortcuts import get_object_or_404

from .models import (
    Farm, House, FlockBatch, DailyRecord, VaccinationRecord,
    VaccinationSchedule, FlockVaccinationSchedule, HealthRecord, HealthAlert,
    TreatmentRecord, FeedType, FeedCategory, FeedingGuide, FeedInventory,
    FeedConsumption, FeedPurchase, FeedConsumptionAlert
)
from .serializers import (
    FarmSerializer, HouseSerializer, FlockBatchSerializer,
    DailyRecordSerializer, DailyRecordCreateSerializer,
    VaccinationRecordSerializer
)
from .vaccination_serializers import (
    VaccinationScheduleSerializer, FlockVaccinationScheduleSerializer
)


def generate_vaccination_schedule_for_batch(batch):
    """Generate vaccination schedule when a new batch is created"""
    bird_type_map = {
        'LAYERS': 'LAYERS',
        'BROILERS': 'BROILERS',
        'DAY_OLD': 'BROILERS',
        'KUROILER': 'KUROILERS',
        'BREEDERS': 'BREEDERS',
    }
    
    bird_type = bird_type_map.get(batch.bird_type, 'LAYERS')
    templates = VaccinationSchedule.objects.filter(bird_type=bird_type)
    
    schedules = []
    for template in templates:
        scheduled_date = batch.start_date + timedelta(weeks=template.week_number)
        schedule = FlockVaccinationSchedule.objects.create(
            batch=batch,
            vaccine_template=template,
            scheduled_date=scheduled_date,
            due_week=template.week_number
        )
        schedules.append(schedule)
    
    return schedules


# ==================== FARM VIEWS ====================

class FarmListCreateView(APIView):
    """List all farms or create a new farm"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user = request.user
        if user.tenant:
            farms = Farm.objects.filter(tenant=user.tenant)
            serializer = FarmSerializer(farms, many=True)
            return Response(serializer.data)
        return Response([])
    
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = FarmSerializer(data=request.data)
        if serializer.is_valid():
            tenant = request.user.tenant
            if not tenant:
                from tenants.models import Tenant
                tenant = Tenant.objects.create(
                    name=f"{request.user.full_name}'s Farm",
                    slug=f"farm_{request.user.id}",
                    is_active=True
                )
                request.user.tenant = tenant
                request.user.save()
            
            farm = serializer.save(tenant=tenant, created_by=request.user)
            return Response(FarmSerializer(farm).data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FarmDetailView(APIView):
    """Get, update or delete a specific farm"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        try:
            farm = Farm.objects.get(pk=pk)
            if farm.tenant != user.tenant and not user.is_superuser:
                return None
            return farm
        except Farm.DoesNotExist:
            return None
    
    def get(self, request, pk):
        farm = self.get_object(pk, request.user)
        if not farm:
            return Response({'error': 'Farm not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = FarmSerializer(farm)
        return Response(serializer.data)
    
    def put(self, request, pk):
        farm = self.get_object(pk, request.user)
        if not farm:
            return Response({'error': 'Farm not found'}, status=status.HTTP_404_NOT_FOUND)
        serializer = FarmSerializer(farm, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        farm = self.get_object(pk, request.user)
        if not farm:
            return Response({'error': 'Farm not found'}, status=status.HTTP_404_NOT_FOUND)
        farm.delete()
        return Response({'message': 'Farm deleted'}, status=status.HTTP_204_NO_CONTENT)


# ==================== HOUSE VIEWS ====================

class HouseListCreateView(APIView):
    """List all houses or create a new house"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        if user.tenant:
            houses = House.objects.filter(tenant=user.tenant)
            serializer = HouseSerializer(houses, many=True)
            return Response(serializer.data)
        return Response([])
    
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = HouseSerializer(data=request.data)
        if serializer.is_valid():
            house = serializer.save(tenant=request.user.tenant)
            return Response(HouseSerializer(house).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HouseDetailView(APIView):
    """Get, update or delete a specific house"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        return get_object_or_404(House, pk=pk, tenant=user.tenant)
    
    def get(self, request, pk):
        house = self.get_object(pk, request.user)
        serializer = HouseSerializer(house)
        return Response(serializer.data)
    
    def put(self, request, pk):
        house = self.get_object(pk, request.user)
        serializer = HouseSerializer(house, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        house = self.get_object(pk, request.user)
        house.delete()
        return Response({'message': 'House deleted'}, status=status.HTTP_204_NO_CONTENT)


# ==================== FLOCK VIEWS ====================

class FlockListCreateView(APIView):
    """List all flocks or create a new flock"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
            
        user = request.user
        if user.tenant:
            flocks = FlockBatch.objects.filter(tenant=user.tenant)
            serializer = FlockBatchSerializer(flocks, many=True)
            return Response(serializer.data)
        return Response([])
    
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = FlockBatchSerializer(data=request.data)
        if serializer.is_valid():
            flock = serializer.save(
                tenant=request.user.tenant,
                created_by=request.user
            )
            generate_vaccination_schedule_for_batch(flock)
            return Response(FlockBatchSerializer(flock).data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FlockDetailView(APIView):
    """Get, update or delete a specific flock"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        return get_object_or_404(FlockBatch, pk=pk, tenant=user.tenant)
    
    def get(self, request, pk):
        flock = self.get_object(pk, request.user)
        serializer = FlockBatchSerializer(flock)
        return Response(serializer.data)
    
    def put(self, request, pk):
        flock = self.get_object(pk, request.user)
        serializer = FlockBatchSerializer(flock, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        flock = self.get_object(pk, request.user)
        flock.delete()
        return Response({'message': 'Flock deleted'}, status=status.HTTP_204_NO_CONTENT)


class AddDailyRecordView(APIView):
    """Add a daily record to a specific flock"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        flock = get_object_or_404(FlockBatch, pk=pk, tenant=request.user.tenant)
        
        serializer = DailyRecordCreateSerializer(data=request.data)
        if serializer.is_valid():
            if not request.data.get('opening_bird_count'):
                serializer.validated_data['opening_bird_count'] = flock.current_quantity
            
            record = serializer.save(
                tenant=request.user.tenant,
                batch=flock,
                recorded_by=request.user
            )
            
            full_serializer = DailyRecordSerializer(record)
            return Response(full_serializer.data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FlockDashboardView(APIView):
    """Get complete dashboard data for a flock"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request, pk):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        batch = get_object_or_404(FlockBatch, pk=pk, tenant=request.user.tenant)
        today = timezone.now().date()
        today_record = batch.daily_records.filter(date=today).first()
        
        # Calculate week start (Monday)
        week_start = today - timedelta(days=today.weekday())
        week_records = batch.daily_records.filter(date__gte=week_start, date__lte=today)
        
        month_start = today.replace(day=1)
        month_records = batch.daily_records.filter(date__gte=month_start, date__lte=today)
        
        week_mortality = week_records.aggregate(total=Sum('mortality'))['total'] or 0
        week_feed = float(week_records.aggregate(total=Sum('feed_consumed_kg'))['total'] or 0)
        week_eggs = week_records.aggregate(total=Sum('eggs_collected'))['total'] or 0
        
        month_expenses = float(month_records.aggregate(total=Sum('total_expenses'))['total'] or 0)
        month_sales = float(month_records.aggregate(total=Sum('sales_revenue'))['total'] or 0)
        
        # Get upcoming vaccinations based on flock start date
        flock_age_weeks = batch.age_weeks
        
        # Map bird type to schedule type
        bird_type_map = {
            'LAYERS': 'LAYERS',
            'BROILERS': 'BROILERS',
            'DAY_OLD': 'BROILERS',
            'KUROILER': 'KUROILERS',
            'BREEDERS': 'BREEDERS',
        }
        
        bird_type = bird_type_map.get(batch.bird_type, 'LAYERS')
        all_schedules = VaccinationSchedule.objects.filter(bird_type=bird_type).order_by('week_number')
        
        # Find upcoming vaccinations based on week number
        upcoming_vaccinations = []
        for schedule in all_schedules:
            if schedule.week_number > flock_age_weeks:
                scheduled_date = batch.start_date + timedelta(weeks=schedule.week_number)
                days_until = (scheduled_date - today).days
                
                if days_until >= 0:
                    upcoming_vaccinations.append({
                        'id': schedule.id,
                        'vaccine': schedule.vaccine_name,
                        'vaccine_type': schedule.vaccine_type,
                        'due_week': schedule.week_number,
                        'scheduled_date': scheduled_date.strftime('%Y-%m-%d'),
                        'days_until': days_until,
                        'administration_method': schedule.administration_method,
                        'dosage': schedule.dosage
                    })
        
        # Also check existing flock vaccination schedules
        existing_schedules = FlockVaccinationSchedule.objects.filter(
            batch=batch,
            status='PENDING',
            scheduled_date__gte=today
        ).order_by('scheduled_date')
        
        # Merge and deduplicate by vaccine name
        existing_vaccine_names = {v['vaccine'] for v in upcoming_vaccinations}
        for vac_schedule in existing_schedules:
            if vac_schedule.vaccine_template.vaccine_name not in existing_vaccine_names:
                upcoming_vaccinations.append({
                    'id': vac_schedule.id,
                    'vaccine': vac_schedule.vaccine_template.vaccine_name,
                    'vaccine_type': vac_schedule.vaccine_template.vaccine_type,
                    'due_week': vac_schedule.due_week,
                    'scheduled_date': vac_schedule.scheduled_date.strftime('%Y-%m-%d'),
                    'days_until': (vac_schedule.scheduled_date - today).days,
                    'administration_method': vac_schedule.vaccine_template.administration_method,
                    'dosage': vac_schedule.vaccine_template.dosage
                })
        
        # Sort by days_until
        upcoming_vaccinations.sort(key=lambda x: x['days_until'])
        
        # Generate alerts
        alerts = []
        if today_record and today_record.alerts_generated:
            alerts = today_record.alerts_generated
        
        for vac in upcoming_vaccinations[:3]:
            if vac['days_until'] <= 3:
                alerts.append({
                    'type': 'VACCINATION_DUE',
                    'message': f"{vac['vaccine']} vaccination due in {vac['days_until']} days",
                    'severity': 'HIGH' if vac['days_until'] <= 1 else 'MEDIUM'
                })
        
        return Response({
            'batch_info': {
                'id': batch.id,
                'name': batch.batch_name,
                'bird_type': batch.bird_type,
                'breed': batch.breed,
                'age_days': batch.age_days,
                'age_weeks': batch.age_weeks,
                'start_date': batch.start_date.strftime('%Y-%m-%d'),
                'status': batch.status,
            },
            'today': {
                'live_birds': today_record.closing_bird_count if today_record else batch.current_quantity,
                'mortality': today_record.mortality if today_record else 0,
                'feed_consumed_kg': float(today_record.feed_consumed_kg) if today_record else 0,
                'water_consumed_liters': float(today_record.water_consumed_liters) if today_record else 0,
                'eggs_collected': today_record.eggs_collected if today_record else 0,
                'avg_weight_kg': float(today_record.avg_weight_kg) if today_record and today_record.avg_weight_kg else None,
                'egg_production_percent': float(today_record.egg_production_percent) if today_record and today_record.egg_production_percent else None,
                'has_record': today_record is not None,
            },
            'this_week': {
                'mortality': week_mortality,
                'mortality_rate': (week_mortality / batch.current_quantity * 100) if batch.current_quantity > 0 else 0,
                'feed_used_kg': week_feed,
                'eggs_produced': week_eggs,
            },
            'this_month': {
                'total_expenses': month_expenses,
                'total_sales': month_sales,
                'gross_profit': month_sales - month_expenses,
            },
            'kpis': {
                'mortality_rate': batch.mortality_rate,
                'survival_rate': batch.survival_rate,
                'feed_conversion_ratio': batch.feed_conversion_ratio,
                'total_eggs_produced': batch.total_eggs_produced,
            },
            'upcoming_vaccinations': upcoming_vaccinations,
            'alerts': alerts,
        })


class CompleteFlockView(APIView):
    """Complete a flock batch"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        batch = get_object_or_404(FlockBatch, pk=pk, tenant=request.user.tenant)
        batch.status = 'COMPLETED'
        batch.end_date = timezone.now().date()
        batch.save()
        
        return Response({
            'message': 'Batch completed successfully',
            'batch_id': batch.id,
            'status': batch.status
        })


# ==================== DAILY RECORD VIEWS ====================

class DailyRecordListCreateView(APIView):
    """List all daily records or create a new one"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user = request.user
        if user.tenant:
            records = DailyRecord.objects.filter(tenant=user.tenant)
            serializer = DailyRecordSerializer(records, many=True)
            return Response(serializer.data)
        return Response([])
    
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = DailyRecordCreateSerializer(data=request.data)
        if serializer.is_valid():
            record = serializer.save(
                tenant=request.user.tenant,
                recorded_by=request.user
            )
            return Response(DailyRecordSerializer(record).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DailyRecordDetailView(APIView):
    """Get, update or delete a specific daily record"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        return get_object_or_404(DailyRecord, pk=pk, tenant=user.tenant)
    
    def get(self, request, pk):
        record = self.get_object(pk, request.user)
        serializer = DailyRecordSerializer(record)
        return Response(serializer.data)
    
    def put(self, request, pk):
        record = self.get_object(pk, request.user)
        serializer = DailyRecordSerializer(record, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        record = self.get_object(pk, request.user)
        record.delete()
        return Response({'message': 'Record deleted'}, status=status.HTTP_204_NO_CONTENT)


# ==================== VACCINATION VIEWS ====================

class VaccinationListCreateView(APIView):
    """List all vaccinations or create a new one"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        user = request.user
        if user.tenant:
            records = VaccinationRecord.objects.filter(tenant=user.tenant)
            serializer = VaccinationRecordSerializer(records, many=True)
            return Response(serializer.data)
        return Response([])
    
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        serializer = VaccinationRecordSerializer(data=request.data)
        if serializer.is_valid():
            record = serializer.save(
                tenant=request.user.tenant,
                created_by=request.user
            )
            
            batch = serializer.validated_data['batch']
            schedule = FlockVaccinationSchedule.objects.filter(
                batch=batch,
                vaccine_template__vaccine_name=serializer.validated_data['vaccine_name']
            ).first()
            
            if schedule:
                schedule.status = 'COMPLETED'
                schedule.completed_date = timezone.now().date()
                schedule.vaccination_record = record
                schedule.save()
            
            return Response(VaccinationRecordSerializer(record).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class VaccinationDetailView(APIView):
    """Get, update or delete a specific vaccination"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        return get_object_or_404(VaccinationRecord, pk=pk, tenant=user.tenant)
    
    def get(self, request, pk):
        record = self.get_object(pk, request.user)
        serializer = VaccinationRecordSerializer(record)
        return Response(serializer.data)
    
    def put(self, request, pk):
        record = self.get_object(pk, request.user)
        serializer = VaccinationRecordSerializer(record, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        record = self.get_object(pk, request.user)
        record.delete()
        return Response({'message': 'Vaccination record deleted'}, status=status.HTTP_204_NO_CONTENT)


class AdministerVaccinationView(APIView):
    """Mark a vaccination as administered"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        vaccination = get_object_or_404(VaccinationRecord, pk=pk, tenant=request.user.tenant)
        vaccination.administered_date = timezone.now().date()
        vaccination.status = 'COMPLETED'
        vaccination.administered_by = request.user.full_name
        vaccination.save()
        
        return Response({
            'message': 'Vaccination administered successfully',
            'vaccination_id': vaccination.id,
            'status': vaccination.status
        })


# ==================== VACCINATION SCHEDULE VIEWS ====================

class VaccinationScheduleListView(APIView):
    """List available vaccination schedules"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        schedules = VaccinationSchedule.objects.all()
        serializer = VaccinationScheduleSerializer(schedules, many=True)
        return Response(serializer.data)


class FlockVaccinationScheduleListView(APIView):
    """List vaccination schedules for a specific flock"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        batch_id = request.query_params.get('batch')
        if batch_id:
            schedules = FlockVaccinationSchedule.objects.filter(
                batch_id=batch_id,
                batch__tenant=request.user.tenant
            ).select_related('vaccine_template')
        else:
            schedules = FlockVaccinationSchedule.objects.filter(batch__tenant=request.user.tenant).select_related('vaccine_template')
        
        # Prepare data with vaccine template details
        data = []
        for schedule in schedules:
            data.append({
                'id': schedule.id,
                'vaccine_name': schedule.vaccine_template.vaccine_name,
                'vaccine_type': schedule.vaccine_template.vaccine_type,
                'vaccine_type_display': schedule.vaccine_template.get_vaccine_type_display(),
                'due_week': schedule.due_week,
                'scheduled_date': schedule.scheduled_date.strftime('%Y-%m-%d'),
                'status': schedule.status,
                'completed_date': schedule.completed_date.strftime('%Y-%m-%d') if schedule.completed_date else None,
                'administration_method': schedule.vaccine_template.administration_method,
                'dosage': schedule.vaccine_template.dosage,
                'is_required': schedule.vaccine_template.is_required,
                'notification_sent': schedule.notification_sent,
                'reminder_sent': schedule.reminder_sent,
            })
        
        return Response(data)

# farm/views.py - Add this class

class RegenerateVaccinationScheduleView(APIView):
    """Regenerate vaccination schedule for a flock"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        batch = get_object_or_404(FlockBatch, pk=pk, tenant=request.user.tenant)
        
        # Delete existing schedules
        from .models import FlockVaccinationSchedule
        FlockVaccinationSchedule.objects.filter(batch=batch).delete()
        
        # Generate new schedules
        from .models import generate_vaccination_schedule_for_batch
        schedules = generate_vaccination_schedule_for_batch(batch)
        
        return Response({
            'message': 'Vaccination schedule regenerated successfully',
            'schedules_count': len(schedules),
            'batch_id': batch.id
        }, status=status.HTTP_200_OK)


class CompleteFlockVaccinationScheduleView(APIView):
    """Mark a vaccination schedule as completed"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        schedule = get_object_or_404(FlockVaccinationSchedule, pk=pk, batch__tenant=request.user.tenant)
        
        # Update schedule
        schedule.status = 'COMPLETED'
        schedule.completed_date = request.data.get('completed_date', timezone.now().date())
        schedule.save()
        
        # Create vaccination record
        from .models import VaccinationRecord
        vaccination_record = VaccinationRecord.objects.create(
            tenant=request.user.tenant,
            batch=schedule.batch,
            schedule=schedule,
            vaccine_type=schedule.vaccine_template.vaccine_type,
            administration_method=schedule.vaccine_template.administration_method,
            dosage=schedule.vaccine_template.dosage,
            scheduled_date=schedule.scheduled_date,
            administered_date=request.data.get('completed_date', timezone.now().date()),
            administered_by=request.data.get('administered_by', ''),
            batch_number=request.data.get('vaccine_batch_number', ''),
            quantity_used=int(request.data.get('quantity_used', 0)),
            cost_per_dose=float(request.data.get('cost_per_dose', 0)),
            reaction_notes=request.data.get('reaction_notes', ''),
            notes=request.data.get('notes', ''),
            status='COMPLETED',
            created_by=request.user
        )
        
        return Response({
            'message': 'Vaccination completed successfully',
            'schedule_id': schedule.id,
            'record_id': vaccination_record.id
        }, status=status.HTTP_200_OK)


class SkipFlockVaccinationScheduleView(APIView):
    """Skip a vaccination schedule"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        schedule = get_object_or_404(FlockVaccinationSchedule, pk=pk, batch__tenant=request.user.tenant)
        schedule.status = 'SKIPPED'
        schedule.save()
        
        return Response({
            'message': 'Vaccination skipped',
            'schedule_id': schedule.id
        }, status=status.HTTP_200_OK)
    

# ==================== HEALTH MONITORING VIEWS ====================

class HealthRecordListCreateView(APIView):
    """List all health records or create a new one"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        batch_id = request.query_params.get('batch')
        user = request.user
        
        if batch_id:
            records = HealthRecord.objects.filter(batch_id=batch_id, batch__tenant=user.tenant)
        elif user.tenant:
            records = HealthRecord.objects.filter(tenant=user.tenant)
        else:
            records = HealthRecord.objects.none()
        
        # Prepare data with display values
        data = []
        for record in records:
            data.append({
                'id': record.id,
                'record_date': record.record_date.strftime('%Y-%m-%d'),
                'health_status': record.health_status,
                'health_status_display': record.get_health_status_display(),
                'disease_type': record.disease_type,
                'disease_type_display': record.get_disease_type_display() if record.disease_type else None,
                'affected_birds_count': record.affected_birds_count,
                'affected_percentage': float(record.affected_percentage),
                'symptoms': record.symptoms,
                'observations': record.observations,
                'temperature_c': float(record.temperature_c) if record.temperature_c else None,
                'humidity_percent': float(record.humidity_percent) if record.humidity_percent else None,
                'reduced_feed_intake': record.reduced_feed_intake,
                'reduced_water_intake': record.reduced_water_intake,
                'respiratory_distress': record.respiratory_distress,
                'diarrhea': record.diarrhea,
                'swollen_eyes': record.swollen_eyes,
                'lethargy': record.lethargy,
                'sudden_death': record.sudden_death,
            })
        
        return Response(data)
    
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        batch_id = request.data.get('batch')
        batch = get_object_or_404(FlockBatch, id=batch_id, tenant=request.user.tenant)
        
        # Create health record
        record = HealthRecord.objects.create(
            tenant=request.user.tenant,
            batch=batch,
            record_date=request.data.get('record_date', timezone.now().date()),
            health_status=request.data.get('health_status', 'GOOD'),
            disease_type=request.data.get('disease_type', ''),
            affected_birds_count=int(request.data.get('affected_birds_count', 0)),
            symptoms=request.data.get('symptoms', ''),
            observations=request.data.get('observations', ''),
            temperature_c=request.data.get('temperature_c'),
            humidity_percent=request.data.get('humidity_percent'),
            reduced_feed_intake=request.data.get('reduced_feed_intake', False),
            reduced_water_intake=request.data.get('reduced_water_intake', False),
            respiratory_distress=request.data.get('respiratory_distress', False),
            diarrhea=request.data.get('diarrhea', False),
            swollen_eyes=request.data.get('swollen_eyes', False),
            lethargy=request.data.get('lethargy', False),
            sudden_death=request.data.get('sudden_death', False),
            recorded_by=request.user
        )
        
        # Create alert if health status is critical or poor
        if record.health_status in ['POOR', 'CRITICAL']:
            HealthAlert.objects.create(
                batch=batch,
                alert_type='SYMPTOM_ALERT',
                severity='HIGH' if record.health_status == 'CRITICAL' else 'MEDIUM',
                title=f"{record.get_health_status_display()} Health Alert",
                message=f"Health status is {record.get_health_status_display()}. {record.affected_birds_count} birds affected.",
                recommended_action="Consult veterinarian immediately. Check feed, water, and environmental conditions.",
                created_by=request.user
            )
        
        return Response({
            'id': record.id,
            'message': 'Health record created successfully'
        }, status=status.HTTP_201_CREATED)


class HealthRecordDetailView(APIView):
    """Get, update or delete a specific health record"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        return get_object_or_404(HealthRecord, pk=pk, tenant=user.tenant)
    
    def get(self, request, pk):
        record = self.get_object(pk, request.user)
        return Response({
            'id': record.id,
            'record_date': record.record_date.strftime('%Y-%m-%d'),
            'health_status': record.health_status,
            'health_status_display': record.get_health_status_display(),
            'disease_type': record.disease_type,
            'disease_type_display': record.get_disease_type_display() if record.disease_type else None,
            'affected_birds_count': record.affected_birds_count,
            'symptoms': record.symptoms,
            'observations': record.observations,
        })
    
    def delete(self, request, pk):
        record = self.get_object(pk, request.user)
        record.delete()
        return Response({'message': 'Health record deleted'}, status=status.HTTP_204_NO_CONTENT)


class TreatmentRecordListCreateView(APIView):
    """List all treatment records or create a new one"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        batch_id = request.query_params.get('batch')
        user = request.user
        
        if batch_id:
            records = TreatmentRecord.objects.filter(batch_id=batch_id, batch__tenant=user.tenant)
        elif user.tenant:
            records = TreatmentRecord.objects.filter(tenant=user.tenant)
        else:
            records = TreatmentRecord.objects.none()
        
        data = []
        for record in records:
            data.append({
                'id': record.id,
                'treatment_type': record.treatment_type,
                'medication_name': record.medication_name,
                'dosage': record.dosage,
                'administration_method': record.administration_method,
                'start_date': record.start_date.strftime('%Y-%m-%d'),
                'duration_days': record.duration_days,
                'quantity_treated': record.quantity_treated,
                'notes': record.notes,
                'effectiveness_notes': record.effectiveness_notes,
            })
        
        return Response(data)
    
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        batch_id = request.data.get('batch')
        batch = get_object_or_404(FlockBatch, id=batch_id, tenant=request.user.tenant)
        
        health_record_id = request.data.get('health_record')
        health_record = None
        if health_record_id:
            health_record = get_object_or_404(HealthRecord, id=health_record_id, tenant=request.user.tenant)
        
        treatment = TreatmentRecord.objects.create(
            tenant=request.user.tenant,
            batch=batch,
            health_record=health_record,
            treatment_type=request.data.get('treatment_type', 'MEDICATION'),
            medication_name=request.data.get('medication_name', ''),
            dosage=request.data.get('dosage', ''),
            administration_method=request.data.get('administration_method', 'DRINKING_WATER'),
            duration_days=int(request.data.get('duration_days', 1)),
            quantity_treated=int(request.data.get('quantity_treated', 0)),
            total_quantity_used=float(request.data.get('total_quantity_used', 0)),
            cost_per_unit=float(request.data.get('cost_per_unit', 0)),
            withdrawal_days=int(request.data.get('withdrawal_days', 0)),
            prescribed_by=request.data.get('prescribed_by', ''),
            notes=request.data.get('notes', ''),
            administered_by=request.user
        )
        
        return Response({
            'id': treatment.id,
            'message': 'Treatment record created successfully'
        }, status=status.HTTP_201_CREATED)


class TreatmentRecordDetailView(APIView):
    """Get, update or delete a specific treatment record"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        return get_object_or_404(TreatmentRecord, pk=pk, tenant=user.tenant)
    
    def delete(self, request, pk):
        record = self.get_object(pk, request.user)
        record.delete()
        return Response({'message': 'Treatment record deleted'}, status=status.HTTP_204_NO_CONTENT)


class HealthAlertListView(APIView):
    """List health alerts for a batch"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        batch_id = request.query_params.get('batch')
        is_resolved = request.query_params.get('is_resolved')
        
        if batch_id:
            alerts = HealthAlert.objects.filter(batch_id=batch_id, batch__tenant=request.user.tenant)
        else:
            alerts = HealthAlert.objects.filter(batch__tenant=request.user.tenant)
        
        if is_resolved is not None:
            alerts = alerts.filter(is_resolved=is_resolved.lower() == 'false')
        
        data = []
        for alert in alerts:
            data.append({
                'id': alert.id,
                'alert_type': alert.alert_type,
                'severity': alert.severity,
                'title': alert.title,
                'message': alert.message,
                'recommended_action': alert.recommended_action,
                'is_resolved': alert.is_resolved,
                'created_at': alert.created_at.strftime('%Y-%m-%d %H:%M'),
            })
        
        return Response(data)


class ResolveHealthAlertView(APIView):
    """Mark a health alert as resolved"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        alert = get_object_or_404(HealthAlert, pk=pk, batch__tenant=request.user.tenant)
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.resolved_by = request.user
        alert.save()
        
        return Response({'message': 'Alert resolved successfully'})
    

# ==================== FEED MANAGEMENT VIEWS ====================
class FeedTypeListView(APIView):
    """List all feed types"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        feed_types = FeedType.objects.filter(is_active=True)
        
        data = []
        for feed_type in feed_types:
            data.append({
                'id': feed_type.id,
                'name': feed_type.name,
                'feed_stage': feed_type.feed_stage,
                'feed_stage_display': feed_type.get_feed_stage_display(),
                'description': feed_type.description,
                'protein_percentage': float(feed_type.protein_percentage) if feed_type.protein_percentage else None,
                'energy_mj_kg': float(feed_type.energy_mj_kg) if feed_type.energy_mj_kg else None,
                'category_name': feed_type.category.name if feed_type.category else None,
                'is_active': feed_type.is_active,
            })
        
        return Response(data)


class FeedingGuideListView(APIView):
    """List feeding guides for a specific bird type"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        bird_type = request.query_params.get('bird_type')
        
        if not bird_type:
            return Response({'error': 'bird_type parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        guides = FeedingGuide.objects.filter(bird_type=bird_type).order_by('week_start')
        
        data = []
        for guide in guides:
            data.append({
                'id': guide.id,
                'bird_type': guide.bird_type,
                'bird_type_display': guide.get_bird_type_display(),
                'week_start': guide.week_start,
                'week_end': guide.week_end,
                'feed_type': guide.feed_type.id,
                'feed_type_name': guide.feed_type.name,
                'daily_feed_per_bird_grams': float(guide.daily_feed_per_bird_grams),
                'expected_weight_kg': float(guide.expected_weight_kg) if guide.expected_weight_kg else None,
                'expected_egg_production': guide.expected_egg_production,
                'notes': guide.notes,
            })
        
        return Response(data)


class FeedInventoryListView(APIView):
    """List feed inventory with optional filtering"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        feed_type_id = request.query_params.get('feed_type')
        user = request.user
        
        if feed_type_id:
            inventory = FeedInventory.objects.filter(
                tenant=user.tenant,
                feed_type_id=feed_type_id,
                is_active=True
            )
        else:
            inventory = FeedInventory.objects.filter(tenant=user.tenant, is_active=True)
        
        data = []
        for item in inventory:
            # Get the most recent purchase to get supplier name
            latest_purchase = FeedPurchase.objects.filter(
                feed_type=item.feed_type,
                tenant=user.tenant
            ).order_by('-purchase_date').first()
            
            data.append({
                'id': item.id,
                'feed_type': item.feed_type.id,
                'feed_type_name': item.feed_type.name,
                'feed_stage': item.feed_type.feed_stage,
                'batch_number': item.batch_number,
                'current_stock_kg': float(item.current_stock_kg),
                'minimum_stock_kg': float(item.minimum_stock_kg),
                'reorder_level_kg': float(item.reorder_level_kg),
                'is_low_stock': item.is_low_stock,
                'needs_reorder': item.needs_reorder,
                'average_cost_per_kg': float(item.average_cost_per_kg),
                'supplier_name': latest_purchase.supplier_name if latest_purchase else item.supplier_name or 'N/A',
                'supplier_contact': latest_purchase.supplier_contact if latest_purchase else item.supplier_contact or 'N/A',
                'last_purchase_date': latest_purchase.purchase_date.strftime('%Y-%m-%d') if latest_purchase else None,
                'last_purchase_quantity_kg': float(latest_purchase.quantity_kg) if latest_purchase else 0,
            })
        
        return Response(data)


class FeedConsumptionListCreateView(APIView):
    """List feed consumption records or create a new one"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        batch_id = request.query_params.get('batch')
        date_filter = request.query_params.get('date')
        
        if not batch_id:
            return Response({'error': 'batch parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        batch = get_object_or_404(FlockBatch, id=batch_id, tenant=request.user.tenant)
        consumptions = FeedConsumption.objects.filter(batch=batch).order_by('-date', 'feeding_time')
        
        if date_filter:
            consumptions = consumptions.filter(date=date_filter)
        
        # Group by date for display
        data = []
        for consumption in consumptions:
            # Calculate actual feed consumed
            feed_given = float(consumption.feed_given_kg) if consumption.feed_given_kg else 0
            feed_remaining = float(consumption.feed_remaining_kg) if consumption.feed_remaining_kg else 0
            feed_consumed = feed_given - feed_remaining
            
            data.append({
                'id': consumption.id,
                'date': consumption.date.strftime('%Y-%m-%d'),
                'feeding_time': consumption.feeding_time,
                'feeding_time_display': consumption.get_feeding_time_display(),
                'feed_type': consumption.feed_type.id,
                'feed_type_name': consumption.feed_type.name,
                'feed_amount_kg': feed_consumed,  # Use calculated value
                'feed_given_kg': feed_given,
                'feed_remaining_kg': feed_remaining,
                'feed_wasted_kg': float(consumption.feed_wasted_kg) if consumption.feed_wasted_kg else 0,
                'bird_count': consumption.bird_count,
                'feed_per_bird_grams': float(consumption.feed_per_bird_grams) if consumption.feed_per_bird_grams else 0,
                'notes': consumption.notes,
                'has_daily_record': consumption.daily_record is not None,
            })
        
        return Response(data)
    
    def post(self, request):
        from decimal import Decimal
        from datetime import datetime
        
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        batch_id = request.data.get('batch')
        if not batch_id:
            return Response({'error': 'batch is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        batch = get_object_or_404(FlockBatch, id=batch_id, tenant=request.user.tenant)
        
        feed_type_id = request.data.get('feed_type')
        if not feed_type_id:
            return Response({'error': 'feed_type is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        feed_type = get_object_or_404(FeedType, id=feed_type_id)
        
        date_str = request.data.get('date')
        if date_str:
            try:
                record_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except ValueError:
                record_date = timezone.now().date()
        else:
            record_date = timezone.now().date()
        
        feeding_time = request.data.get('feeding_time', 'MORNING')
        
        # Get values from request
        try:
            current_stock = Decimal(str(request.data.get('current_stock', 0)))
            feed_given = Decimal(str(request.data.get('feed_given_kg', 0)))
            feed_remaining = Decimal(str(request.data.get('feed_remaining_kg', 0)))
            bird_count = int(request.data.get('bird_count', batch.current_quantity))
        except (ValueError, TypeError) as e:
            return Response({'error': f'Invalid numeric value: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Check if there's a daily record for this date
        daily_record = DailyRecord.objects.filter(batch=batch, date=record_date).first()
        
        # Create or update consumption record
        consumption, created = FeedConsumption.objects.update_or_create(
            batch=batch,
            date=record_date,
            feeding_time=feeding_time,
            feed_type=feed_type,
            defaults={
                'tenant': request.user.tenant,
                'daily_record': daily_record,
                'current_stock_kg': current_stock,
                'feed_given_kg': feed_given,
                'feed_remaining_kg': feed_remaining,
                'bird_count': bird_count,
                'notes': request.data.get('notes', ''),
                'recorded_by': request.user
            }
        )
        
        # Update daily record's total feed consumed
        if daily_record:
            total_consumption = FeedConsumption.objects.filter(
                batch=batch, 
                date=record_date
            ).aggregate(total=Sum('feed_consumed_kg'))['total'] or Decimal('0')
            
            daily_record.feed_consumed_kg = total_consumption
            daily_record.save(update_fields=['feed_consumed_kg'])
        
        return Response({
            'id': consumption.id,
            'created': created,
            'date': record_date.strftime('%Y-%m-%d'),
            'feeding_time': feeding_time,
            'feed_consumed_kg': float(consumption.feed_consumed_kg),
            'message': f'{consumption.get_feeding_time_display()} feed consumption recorded successfully'
        }, status=status.HTTP_201_CREATED)
    
class FeedConsumptionDetailView(APIView):
    """Get, update or delete a specific feed consumption record"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        return get_object_or_404(FeedConsumption, pk=pk, tenant=user.tenant)
    
    def get(self, request, pk):
        """Get a single feed consumption record for editing"""
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        consumption = self.get_object(pk, request.user)
        
        # Calculate actual feed consumed
        feed_given = float(consumption.feed_given_kg) if consumption.feed_given_kg else 0
        feed_remaining = float(consumption.feed_remaining_kg) if consumption.feed_remaining_kg else 0
        feed_consumed = feed_given - feed_remaining
        
        return Response({
            'id': consumption.id,
            'batch': consumption.batch.id,
            'date': consumption.date.strftime('%Y-%m-%d'),
            'feeding_time': consumption.feeding_time,
            'feed_type': consumption.feed_type.id,
            'feed_type_name': consumption.feed_type.name,
            'feed_amount_kg': feed_consumed,
            'feed_given_kg': feed_given,
            'feed_remaining_kg': feed_remaining,
            'bird_count': consumption.bird_count,
            'notes': consumption.notes or '',
        })
    
    def put(self, request, pk):
        """Update a feed consumption record"""
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        consumption = self.get_object(pk, request.user)
        
        # Update fields
        consumption.date = request.data.get('date', consumption.date)
        consumption.feeding_time = request.data.get('feeding_time', consumption.feeding_time)
        consumption.feed_given_kg = Decimal(str(request.data.get('feed_given_kg', 0)))
        consumption.feed_remaining_kg = Decimal(str(request.data.get('feed_remaining_kg', 0)))
        consumption.bird_count = int(request.data.get('bird_count', consumption.bird_count))
        consumption.notes = request.data.get('notes', '')
        
        # Update feed type if changed
        feed_type_id = request.data.get('feed_type')
        if feed_type_id and feed_type_id != consumption.feed_type.id:
            consumption.feed_type = get_object_or_404(FeedType, id=feed_type_id)
        
        # Save will recalculate feed_consumed_kg
        consumption.save()
        
        # Update daily record if exists
        if consumption.daily_record:
            total_consumption = FeedConsumption.objects.filter(
                batch=consumption.batch,
                date=consumption.date
            ).aggregate(total=Sum('feed_consumed_kg'))['total'] or Decimal('0')
            
            consumption.daily_record.feed_consumed_kg = total_consumption
            consumption.daily_record.save(update_fields=['feed_consumed_kg'])
        
        return Response({
            'id': consumption.id,
            'message': 'Consumption record updated successfully',
            'feed_consumed_kg': float(consumption.feed_consumed_kg)
        })
    
    def delete(self, request, pk):
        """Delete a feed consumption record"""
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        consumption = self.get_object(pk, request.user)
        
        # Store reference to daily record before deletion
        daily_record = consumption.daily_record
        batch = consumption.batch
        record_date = consumption.date
        
        consumption.delete()
        
        # Update daily record's total feed consumed
        if daily_record:
            total_consumption = FeedConsumption.objects.filter(
                batch=batch,
                date=record_date
            ).aggregate(total=Sum('feed_consumed_kg'))['total'] or Decimal('0')
            
            daily_record.feed_consumed_kg = total_consumption
            daily_record.save(update_fields=['feed_consumed_kg'])
        
        return Response({'message': 'Consumption record deleted successfully'})

class FeedPurchaseCreateView(APIView):
    """Create a new feed purchase record"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        feed_type_id = request.data.get('feed_type')
        feed_type = get_object_or_404(FeedType, id=feed_type_id)
        
        # Get or create inventory for this feed type
        inventory, created = FeedInventory.objects.get_or_create(
            tenant=request.user.tenant,
            feed_type=feed_type,
            defaults={
                'current_stock_kg': 0,
                'minimum_stock_kg': 100,
                'reorder_level_kg': 200,
                'is_active': True
            }
        )
        
        purchase = FeedPurchase.objects.create(
            tenant=request.user.tenant,
            feed_type=feed_type,
            inventory=inventory,
            purchase_date=request.data.get('purchase_date', timezone.now().date()),
            invoice_number=request.data.get('invoice_number', ''),
            quantity_kg=float(request.data.get('quantity_kg', 0)),
            cost_per_kg=float(request.data.get('cost_per_kg', 0)),
            supplier_name=request.data.get('supplier_name', ''),
            supplier_contact=request.data.get('supplier_contact', ''),
            delivery_date=request.data.get('delivery_date'),
            delivery_notes=request.data.get('delivery_notes', ''),
            payment_status=request.data.get('payment_status', 'PENDING'),
            notes=request.data.get('notes', ''),
            created_by=request.user
        )
        
        return Response({
            'id': purchase.id,
            'message': 'Feed purchase recorded successfully',
            'inventory_updated': not created
        }, status=status.HTTP_201_CREATED)


class FeedAlertListView(APIView):
    """List feed consumption alerts for a batch"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        batch_id = request.query_params.get('batch')
        is_resolved = request.query_params.get('is_resolved')
        
        if not batch_id:
            return Response({'error': 'batch parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        batch = get_object_or_404(FlockBatch, id=batch_id, tenant=request.user.tenant)
        alerts = FeedConsumptionAlert.objects.filter(batch=batch)
        
        if is_resolved is not None:
            alerts = alerts.filter(is_resolved=is_resolved.lower() == 'false')
        
        data = []
        for alert in alerts:
            data.append({
                'id': alert.id,
                'alert_date': alert.alert_date.strftime('%Y-%m-%d'),
                'severity': alert.severity,
                'title': alert.title,
                'message': alert.message,
                'recommended_feed_kg': float(alert.recommended_feed_kg) if alert.recommended_feed_kg else None,
                'current_consumption_kg': float(alert.current_consumption_kg) if alert.current_consumption_kg else None,
                'recommended_per_bird_grams': alert.recommended_per_bird_grams,
                'current_per_bird_grams': alert.current_per_bird_grams,
                'bird_count': alert.bird_count,
                'week_number': alert.week_number,
                'is_resolved': alert.is_resolved,
                'created_at': alert.created_at.strftime('%Y-%m-%d %H:%M'),
            })
        
        return Response(data)


class ResolveFeedAlertView(APIView):
    """Mark a feed alert as resolved"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, pk):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        alert = get_object_or_404(FeedConsumptionAlert, pk=pk, batch__tenant=request.user.tenant)
        alert.is_resolved = True
        alert.save()
        
        return Response({
            'message': 'Alert resolved successfully',
            'alert_id': alert.id
        }, status=status.HTTP_200_OK)


class FeedSummaryView(APIView):
    """Get feed summary - cost comes ONLY from FeedPurchase"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from decimal import Decimal
        from datetime import timedelta
        
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        batch_id = request.query_params.get('batch')
        
        if not batch_id:
            return Response({'error': 'batch parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        batch = get_object_or_404(FlockBatch, id=batch_id, tenant=request.user.tenant)
        
        # Get total consumption from FeedConsumption records
        total_consumption = FeedConsumption.objects.filter(batch=batch).aggregate(
            total=Sum('feed_consumed_kg')
        )['total'] or Decimal('0')
        
        # Get all feed types used by this batch
        feed_types_used = FeedConsumption.objects.filter(batch=batch).values_list('feed_type', flat=True).distinct()
        
        # TOTAL FEED COST = SUM OF ALL PURCHASES (regardless of consumption)
        total_purchase_cost = Decimal('0')
        for feed_type_id in feed_types_used:
            purchases = FeedPurchase.objects.filter(
                feed_type_id=feed_type_id,
                tenant=request.user.tenant
            )
            for purchase in purchases:
                total_purchase_cost += purchase.total_cost
        
        total_feed_cost = float(total_purchase_cost)
        
        # Get today's consumption
        today = timezone.now().date()
        today_consumption = FeedConsumption.objects.filter(
            batch=batch,
            date=today
        ).aggregate(total=Sum('feed_consumed_kg'))['total'] or Decimal('0')
        
        # Get last 7 days consumption
        week_ago = today - timedelta(days=7)
        week_consumption = FeedConsumption.objects.filter(
            batch=batch,
            date__gte=week_ago
        ).aggregate(total=Sum('feed_consumed_kg'))['total'] or Decimal('0')
        
        # Calculate average daily consumption
        consumption_count = FeedConsumption.objects.filter(batch=batch).count()
        avg_daily = float(total_consumption / consumption_count) if consumption_count > 0 else 0
        
        # Calculate FCR
        daily_records = DailyRecord.objects.filter(batch=batch).exclude(weight_gain_kg__isnull=True)
        total_weight_gain = daily_records.aggregate(total=Sum('weight_gain_kg'))['total'] or 0
        
        if total_weight_gain > 0:
            fcr = float(total_consumption / Decimal(str(total_weight_gain)))
        else:
            expected_weight = 1.5
            total_expected_weight = batch.current_quantity * expected_weight
            fcr = float(total_consumption / Decimal(str(total_expected_weight))) if total_expected_weight > 0 else 0
        
        feed_efficiency = (1 / fcr * 100) if fcr > 0 else 0
        
        # Get feeding guide recommendation
        current_guide = FeedingGuide.objects.filter(
            bird_type=batch.bird_type,
            week_start__lte=batch.age_weeks,
            week_end__gte=batch.age_weeks
        ).first()
        
        recommended_daily = 0
        if current_guide:
            recommended_daily = float((current_guide.daily_feed_per_bird_grams * batch.current_quantity) / 1000)
        
        return Response({
            'total_feed_consumed_kg': float(total_consumption),
            'total_feed_cost': total_feed_cost,  # This is the SUM of all purchases
            'today_feed_consumption_kg': float(today_consumption),
            'weekly_feed_consumption_kg': float(week_consumption),
            'average_daily_consumption_kg': avg_daily,
            'recommended_daily_consumption_kg': recommended_daily,
            'feed_conversion_ratio_fcr': round(fcr, 2),
            'feed_efficiency_percent': round(feed_efficiency, 1),
            'total_bird_count': batch.current_quantity,
            'age_days': batch.age_days,
            'age_weeks': batch.age_weeks,
        })
    

class FeedPurchaseSummaryView(APIView):
    """Get summary of feed purchases - returns total cost sum of all purchases"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        from decimal import Decimal
        
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        batch_id = request.query_params.get('batch')
        
        if not batch_id:
            return Response({'error': 'batch parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        batch = get_object_or_404(FlockBatch, id=batch_id, tenant=request.user.tenant)
        
        # Get ALL feed purchases for this tenant (not filtered by feed type)
        # Because all feed purchases are relevant to the farm
        all_purchases = FeedPurchase.objects.filter(tenant=request.user.tenant)
        
        # Calculate total cost from ALL purchases
        total_purchase_cost = all_purchases.aggregate(
            total=Sum('total_cost')
        )['total'] or Decimal('0')
        
        # Get purchase details
        purchase_details = []
        for purchase in all_purchases.order_by('-purchase_date'):
            purchase_details.append({
                'id': purchase.id,
                'feed_type': purchase.feed_type.name,
                'date': purchase.purchase_date.strftime('%Y-%m-%d'),
                'quantity_kg': float(purchase.quantity_kg),
                'cost_per_kg': float(purchase.cost_per_kg),
                'total_cost': float(purchase.total_cost),
                'supplier': purchase.supplier_name,
                'invoice_number': purchase.invoice_number
            })
        
        return Response({
            'total_purchase_cost': float(total_purchase_cost),
            'purchase_count': all_purchases.count(),
            'purchase_details': purchase_details
        })
    
class DailyRecordFeedSummaryView(APIView):
    """Get feed summary from daily records for a batch"""
    authentication_classes = [SessionAuthentication, BasicAuthentication]
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        if not request.user.is_authenticated:
            return Response({'error': 'Not authenticated'}, status=status.HTTP_401_UNAUTHORIZED)
        
        batch_id = request.query_params.get('batch')
        
        if not batch_id:
            return Response({'error': 'batch parameter is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        batch = get_object_or_404(FlockBatch, id=batch_id, tenant=request.user.tenant)
        
        # Get daily records
        daily_records = DailyRecord.objects.filter(batch=batch).order_by('date')
        
        # Calculate feed statistics from daily records
        total_feed_consumed = daily_records.aggregate(total=Sum('feed_consumed_kg'))['total'] or 0
        total_feed_cost = daily_records.aggregate(total=Sum('feed_cost'))['total'] or 0
        
        # Calculate average daily consumption
        avg_daily = daily_records.aggregate(avg=Avg('feed_consumed_kg'))['avg'] or 0
        
        # Calculate FCR from daily records weight data
        fcr_data = []
        for record in daily_records:
            if record.feed_conversion_ratio:
                fcr_data.append({
                    'date': record.date,
                    'fcr': float(record.feed_conversion_ratio),
                    'weight_gain': float(record.weight_gain_kg) if record.weight_gain_kg else 0,
                    'feed_consumed': float(record.feed_consumed_kg)
                })
        
        # Get current feeding guide recommendation
        current_guide = FeedingGuide.objects.filter(
            bird_type=batch.bird_type,
            week_start__lte=batch.age_weeks,
            week_end__gte=batch.age_weeks
        ).first()
        
        recommended_daily = 0
        if current_guide:
            recommended_daily = (current_guide.daily_feed_per_bird_grams * batch.current_quantity) / 1000
        
        return Response({
            'batch_info': {
                'id': batch.id,
                'name': batch.batch_name,
                'bird_type': batch.bird_type,
                'current_quantity': batch.current_quantity,
                'age_days': batch.age_days,
                'age_weeks': batch.age_weeks
            },
            'feed_statistics': {
                'total_feed_consumed_kg': float(total_feed_consumed),
                'total_feed_cost': float(total_feed_cost),
                'average_daily_consumption_kg': float(avg_daily),
                'recommended_daily_consumption_kg': float(recommended_daily),
                'consumption_variance_percent': float(((avg_daily - recommended_daily) / recommended_daily) * 100) if recommended_daily > 0 else 0
            },
            'fcr_trend': fcr_data,
            'recent_records': DailyRecordSerializer(daily_records[:30], many=True).data
        })

# ==================== TEST VIEW ====================

@api_view(['GET'])
def test_farm_view(request):
    """Simple test endpoint to verify API is working"""
    return Response({
        'status': 'ok',
        'message': 'Farm API is working!',
        'authenticated': request.user.is_authenticated,
        'user': str(request.user),
        'endpoints': {
            'farms': '/api/v1/farms/farms/',
            'houses': '/api/v1/farms/houses/',
            'flocks': '/api/v1/farms/flocks/',
            'daily_records': '/api/v1/farms/daily-records/',
            'vaccinations': '/api/v1/farms/vaccinations/',
        }
    })