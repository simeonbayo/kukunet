# farm/views.py
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Farm, House, FlockBatch, DailyRecord, VaccinationRecord, Expense
from .serializers import (
    FarmSerializer, HouseSerializer, FlockBatchSerializer,
    DailyRecordSerializer, VaccinationSerializer, ExpenseSerializer
)

class FarmViewSet(viewsets.ModelViewSet):
    serializer_class = FarmSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return Farm.objects.filter(tenant=self.request.tenant)
        return Farm.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

class HouseViewSet(viewsets.ModelViewSet):
    serializer_class = HouseSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return House.objects.filter(tenant=self.request.tenant)
        return House.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

class FlockBatchViewSet(viewsets.ModelViewSet):
    serializer_class = FlockBatchSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['status', 'bird_type', 'farm']
    
    def get_queryset(self):
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return FlockBatch.objects.filter(tenant=self.request.tenant)
        return FlockBatch.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)
    
    @action(detail=True, methods=['post'])
    def add_daily_record(self, request, pk=None):
        batch = self.get_object()
        serializer = DailyRecordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(tenant=request.tenant, batch=batch)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DailyRecordViewSet(viewsets.ModelViewSet):
    serializer_class = DailyRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['batch', 'date']
    
    def get_queryset(self):
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return DailyRecord.objects.filter(tenant=self.request.tenant)
        return DailyRecord.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

class VaccinationRecordViewSet(viewsets.ModelViewSet):
    serializer_class = VaccinationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return VaccinationRecord.objects.filter(tenant=self.request.tenant)
        return VaccinationRecord.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant)

class ExpenseViewSet(viewsets.ModelViewSet):
    serializer_class = ExpenseSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        if hasattr(self.request, 'tenant') and self.request.tenant:
            return Expense.objects.filter(tenant=self.request.tenant)
        return Expense.objects.none()
    
    def perform_create(self, serializer):
        serializer.save(tenant=self.request.tenant, created_by=self.request.user)