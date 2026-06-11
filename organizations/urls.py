# organizations/urls.py
from django.urls import path
from django.views.generic import TemplateView
from .views import (
    OrganizationDashboardStatsView,
    OrganizationFarmersView,
    OrganizationFlocksView,
    OrganizationFlockDetailView,
    OrganizationDailyRecordsView,
    OrganizationFeedPurchasesView,
    OrganizationOrdersView,
    OrganizationFarmerDetailView
)

urlpatterns = [
    path('stats/', OrganizationDashboardStatsView.as_view(), name='org-stats'),
    path('farmers/', OrganizationFarmersView.as_view(), name='org-farmers'),
    path('farmers/<int:farmer_id>/', OrganizationFarmerDetailView.as_view(), name='org-farmer-detail'),
    path('flocks/', OrganizationFlocksView.as_view(), name='org-flocks'),
    path('flocks/<int:flock_id>/', OrganizationFlockDetailView.as_view(), name='org-flock-detail'),
    path('daily-records/', OrganizationDailyRecordsView.as_view(), name='org-daily-records'),
    path('feed-purchases/', OrganizationFeedPurchasesView.as_view(), name='org-feed-purchases'),
    path('orders/', OrganizationOrdersView.as_view(), name='org-orders'),
    path('orders/<int:order_id>/', OrganizationOrdersView.as_view(), name='org-order-update'),
    path('organizations/farmers/<int:farmer_id>/', TemplateView.as_view(template_name='dashboard/organizations/farmer_detail.html'), name='farmer-detail-html'),
]