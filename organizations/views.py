# organizations/views.py
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import OrganizationFarmer, OrganizationProject, OrganizationMember, Partnership
from .serializers import (
    OrganizationFarmerSerializer, OrganizationProjectSerializer,
    OrganizationMemberSerializer, PartnershipSerializer
)
from accounts.models import User
from farm.models import FlockBatch, DailyRecord

class OrganizationFarmerViewSet(viewsets.ModelViewSet):
    """ViewSet for managing organization farmers"""
    serializer_class = OrganizationFarmerSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Return only farmers belonging to this organization"""
        if self.request.user.role == 'ORGANIZATION':
            return OrganizationFarmer.objects.filter(organization=self.request.user)
        return OrganizationFarmer.objects.none()
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Get farmer statistics for dashboard"""
        farmers = self.get_queryset()
        
        total_farmers = farmers.count()
        active_farmers = farmers.filter(is_active=True).count()
        
        # Get bird statistics from linked farm data
        total_birds = 0
        daily_eggs = 0
        monthly_eggs = 0
        
        for farmer in farmers:
            if farmer.farm:
                batches = FlockBatch.objects.filter(farm=farmer.farm, status='ACTIVE')
                total_birds += batches.aggregate(Sum('quantity'))['quantity__sum'] or 0
                
                # Get today's egg production
                today_records = DailyRecord.objects.filter(
                    batch__farm=farmer.farm,
                    date=timezone.now().date()
                )
                daily_eggs += today_records.aggregate(Sum('eggs_collected'))['eggs_collected__sum'] or 0
        
        return Response({
            'total_farmers': total_farmers,
            'active_farmers': active_farmers,
            'total_birds': total_birds,
            'avg_birds_per_farmer': round(total_birds / total_farmers, 1) if total_farmers > 0 else 0,
            'daily_egg_production': daily_eggs,
            'monthly_egg_production': monthly_eggs,
            'total_revenue': 0,  # Calculate from orders
            'quarterly_revenue': 0,
        })
    
    @action(detail=False, methods=['get'])
    def list_farmers(self, request):
        """List all farmers with pagination and filtering"""
        farmers = self.get_queryset()
        
        # Apply filters
        search = request.query_params.get('search', '')
        village = request.query_params.get('village', '')
        
        if search:
            farmers = farmers.filter(
                Q(name__icontains=search) | 
                Q(phone__icontains=search) |
                Q(village__icontains=search)
            )
        
        if village:
            farmers = farmers.filter(village=village)
        
        # Pagination
        page = int(request.query_params.get('page', 1))
        page_size = 20
        start = (page - 1) * page_size
        end = start + page_size
        
        total = farmers.count()
        farmers_list = farmers[start:end]
        
        # Prepare farmer data with farm stats
        farmer_data = []
        for farmer in farmers_list:
            bird_count = 0
            daily_eggs = 0
            if farmer.farm:
                batches = FlockBatch.objects.filter(farm=farmer.farm, status='ACTIVE')
                bird_count = batches.aggregate(Sum('quantity'))['quantity__sum'] or 0
                
                today_records = DailyRecord.objects.filter(
                    batch__farm=farmer.farm,
                    date=timezone.now().date()
                )
                daily_eggs = today_records.aggregate(Sum('eggs_collected'))['eggs_collected__sum'] or 0
            
            farmer_data.append({
                'id': farmer.id,
                'name': farmer.name,
                'phone': farmer.phone,
                'village': farmer.village,
                'district': farmer.district,
                'joined_date': farmer.created_at,
                'is_active': farmer.is_active,
                'total_birds': bird_count,
                'daily_eggs': daily_eggs,
            })
        
        return Response({
            'farmers': farmer_data,
            'total': total,
            'total_pages': (total + page_size - 1) // page_size,
            'current_page': page,
        })
    
    @action(detail=False, methods=['get'])
    def top(self, request):
        """Get top performing farmers"""
        farmers = self.get_queryset().filter(is_active=True)
        
        top_farmers = []
        for farmer in farmers:
            daily_eggs = 0
            if farmer.farm:
                today_records = DailyRecord.objects.filter(
                    batch__farm=farmer.farm,
                    date=timezone.now().date()
                )
                daily_eggs = today_records.aggregate(Sum('eggs_collected'))['eggs_collected__sum'] or 0
            
            top_farmers.append({
                'id': farmer.id,
                'name': farmer.name,
                'village': farmer.village,
                'daily_eggs': daily_eggs,
                'total_birds': 0,
            })
        
        # Sort by daily eggs
        top_farmers.sort(key=lambda x: x['daily_eggs'], reverse=True)
        
        return Response({'farmers': top_farmers[:10]})
    
    @action(detail=False, methods=['get'])
    def activity(self, request):
        """Get recent farmer activity"""
        # This would typically come from an activity log model
        return Response({'activities': []})
    
    @action(detail=False, methods=['get'])
    def distribution(self, request):
        """Get farmer distribution by village"""
        farmers = self.get_queryset()
        
        distribution = {}
        for farmer in farmers:
            village = farmer.village or 'Unknown'
            distribution[village] = distribution.get(village, 0) + 1
        
        return Response({
            'villages': list(distribution.keys()),
            'counts': list(distribution.values()),
        })
    
    @action(detail=False, methods=['get'])
    def villages(self, request):
        """Get list of villages with farmers"""
        farmers = self.get_queryset()
        villages = list(set(farmer.village for farmer in farmers if farmer.village))
        return Response({'villages': sorted(villages)})
    
    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        """Get detailed farmer information"""
        farmer = self.get_object()
        
        bird_count = 0
        daily_eggs = 0
        mortality_rate = 0
        
        if farmer.farm:
            batches = FlockBatch.objects.filter(farm=farmer.farm)
            bird_count = batches.aggregate(Sum('quantity'))['quantity__sum'] or 0
            
            # Calculate mortality rate
            total_mortality = 0
            for batch in batches:
                total_mortality += batch.daily_records.aggregate(Sum('mortality'))['mortality__sum'] or 0
            
            if bird_count > 0:
                mortality_rate = round((total_mortality / bird_count) * 100, 1)
            
            today_records = DailyRecord.objects.filter(
                batch__farm=farmer.farm,
                date=timezone.now().date()
            )
            daily_eggs = today_records.aggregate(Sum('eggs_collected'))['eggs_collected__sum'] or 0
        
        return Response({
            'id': farmer.id,
            'name': farmer.name,
            'phone': farmer.phone,
            'village': farmer.village,
            'district': farmer.district,
            'joined_date': farmer.created_at,
            'is_active': farmer.is_active,
            'total_birds': bird_count,
            'daily_eggs': daily_eggs,
            'mortality_rate': mortality_rate,
            'farm_type': farmer.farm.farm_type if farmer.farm else None,
            'notes': farmer.notes,
            'total_sales': 0,
        })
    
    @action(detail=True, methods=['get'])
    def production(self, request, pk=None):
        """Get production history for a farmer"""
        farmer = self.get_object()
        
        production_data = []
        if farmer.farm:
            # Get last 30 days of production
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=30)
            
            records = DailyRecord.objects.filter(
                batch__farm=farmer.farm,
                date__gte=start_date,
                date__lte=end_date
            ).order_by('date')
            
            dates = []
            eggs = []
            for record in records:
                dates.append(record.date.strftime('%Y-%m-%d'))
                eggs.append(record.eggs_collected)
            
            production_data = {
                'dates': dates,
                'production': eggs,
            }
        
        return Response(production_data)
    
    @action(detail=False, methods=['post'])
    def add(self, request):
        """Add a new farmer to the organization"""
        serializer = self.get_serializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                'success': False,
                'message': 'Validation failed',
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Create user account for farmer
        pin = request.data.get('pin', '1234')
        phone = request.data.get('phone')
        name = request.data.get('name')
        
        user, created = User.objects.get_or_create(
            phone_number=phone,
            defaults={
                'full_name': name,
                'role': 'FARMER',
                'tenant': request.user.tenant,
            }
        )
        
        if created:
            user.set_pin(pin)
            user.save()
        
        farmer = serializer.save(
            organization=request.user,
            user=user,
            created_by=request.user
        )
        
        return Response({
            'success': True,
            'message': 'Farmer added successfully',
            'farmer_id': farmer.id
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['delete'])
    def delete(self, request, pk=None):
        """Remove a farmer from the organization"""
        farmer = self.get_object()
        farmer.delete()
        return Response({
            'success': True,
            'message': 'Farmer removed successfully'
        })
    
    @action(detail=False, methods=['get'])
    def template(self, request):
        """Download CSV template for importing farmers"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="farmer_template.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['Name', 'Phone', 'Village', 'District', 'Farm Type', 'Notes'])
        writer.writerow(['John Doe', '256712345678', 'Kampala', 'Kampala', 'LAYERS', ''])
        
        return response
    
    @action(detail=False, methods=['post'])
    def import_farmers(self, request):
        """Import farmers from CSV file"""
        import csv
        import io
        
        file = request.FILES.get('file')
        if not file:
            return Response({'message': 'No file provided'}, status=400)
        
        imported = 0
        errors = []
        
        # Parse CSV
        decoded_file = file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.DictReader(io_string)
        
        for row in reader:
            try:
                # Create farmer
                farmer = OrganizationFarmer.objects.create(
                    organization=request.user,
                    name=row.get('Name'),
                    phone=row.get('Phone'),
                    village=row.get('Village'),
                    district=row.get('District'),
                    farm_type=row.get('Farm Type', 'LAYERS'),
                    notes=row.get('Notes', ''),
                    created_by=request.user
                )
                imported += 1
            except Exception as e:
                errors.append(str(e))
        
        return Response({
            'imported': imported,
            'errors': errors,
            'message': f'Successfully imported {imported} farmers'
        })