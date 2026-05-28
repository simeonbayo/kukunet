# farm/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'farms', views.FarmViewSet, basename='farm')
router.register(r'houses', views.HouseViewSet, basename='house')
router.register(r'flocks', views.FlockBatchViewSet, basename='flockbatch')
router.register(r'daily-records', views.DailyRecordViewSet, basename='dailyrecord')
router.register(r'vaccinations', views.VaccinationRecordViewSet, basename='vaccination')
router.register(r'expenses', views.ExpenseViewSet, basename='expense')

urlpatterns = [
    path('', include(router.urls)),
]