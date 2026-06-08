from django.urls import path
from . import views

 
urlpatterns = [
    # Add your path configurations here
    path('farmer/dashboard/', views.FarmerDashboardAnalyticsView.as_view(), name='farmer-dashboard'),
    path('farmer/flocks/', views.FarmerFlocksAnalyticsView.as_view(), name='farmer-flocks'),
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
]
