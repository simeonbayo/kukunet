# farm/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Farm endpoints
    path('farms/', views.FarmListCreateView.as_view(), name='farm-list-create'),
    path('farms/<int:pk>/', views.FarmDetailView.as_view(), name='farm-detail'),
    
    # House endpoints
    path('houses/', views.HouseListCreateView.as_view(), name='house-list-create'),
    path('houses/<int:pk>/', views.HouseDetailView.as_view(), name='house-detail'),
    
    # Flock endpoints
    path('flocks/', views.FlockListCreateView.as_view(), name='flock-list-create'),
    path('flocks/<int:pk>/', views.FlockDetailView.as_view(), name='flock-detail'),
    path('flocks/<int:pk>/add-daily-record/', views.AddDailyRecordView.as_view(), name='flock-add-daily-record'),
    path('flocks/<int:pk>/dashboard/', views.FlockDashboardView.as_view(), name='flock-dashboard'),
    path('flocks/<int:pk>/complete/', views.CompleteFlockView.as_view(), name='flock-complete'),
    
    # Daily Record endpoints
    path('daily-records/', views.DailyRecordListCreateView.as_view(), name='daily-record-list-create'),
    path('daily-records/<int:pk>/', views.DailyRecordDetailView.as_view(), name='daily-record-detail'),
    
    # Vaccination endpoints
    path('vaccinations/', views.VaccinationListCreateView.as_view(), name='vaccination-list-create'),
    path('vaccinations/<int:pk>/', views.VaccinationDetailView.as_view(), name='vaccination-detail'),
    path('vaccinations/<int:pk>/administer/', views.AdministerVaccinationView.as_view(), name='vaccination-administer'),

    path('flock-vaccination-schedules/', views.FlockVaccinationScheduleListView.as_view(), name='flock-vaccination-schedule-list'),
    path('flock-vaccination-schedules/<int:pk>/complete/', views.CompleteFlockVaccinationScheduleView.as_view(), name='flock-vaccination-complete'),
    path('flock-vaccination-schedules/<int:pk>/skip/', views.SkipFlockVaccinationScheduleView.as_view(), name='flock-vaccination-skip'),
    path('flocks/<int:pk>/regenerate-vaccination-schedule/', views.RegenerateVaccinationScheduleView.as_view(), name='regenerate-vaccination-schedule'),
    
    # Vaccination Schedule endpoints
    path('vaccination-schedules/', views.VaccinationScheduleListView.as_view(), name='vaccination-schedule-list'),
    path('flock-vaccination-schedules/', views.FlockVaccinationScheduleListView.as_view(), name='flock-vaccination-schedule-list'),

    # Health Monitoring URLs
    path('health-records/', views.HealthRecordListCreateView.as_view(), name='health-record-list'),
    path('health-records/<int:pk>/', views.HealthRecordDetailView.as_view(), name='health-record-detail'),
    path('treatment-records/', views.TreatmentRecordListCreateView.as_view(), name='treatment-record-list'),
    path('treatment-records/<int:pk>/', views.TreatmentRecordDetailView.as_view(), name='treatment-record-detail'),
    path('health-alerts/', views.HealthAlertListView.as_view(), name='health-alert-list'),
    path('health-alerts/<int:pk>/resolve/', views.ResolveHealthAlertView.as_view(), name='health-alert-resolve'),

    # Feed Management URLs
    path('feed-types/', views.FeedTypeListView.as_view(), name='feed-type-list'),
    path('feeding-guides/', views.FeedingGuideListView.as_view(), name='feeding-guide-list'),
    path('feed-inventory/', views.FeedInventoryListView.as_view(), name='feed-inventory-list'),
    path('feed-consumption/', views.FeedConsumptionListCreateView.as_view(), name='feed-consumption-list'),
    path('feed-purchases/', views.FeedPurchaseCreateView.as_view(), name='feed-purchase-create'),
    path('feed-alerts/', views.FeedAlertListView.as_view(), name='feed-alert-list'),
    path('feed-alerts/<int:pk>/resolve/', views.ResolveFeedAlertView.as_view(), name='feed-alert-resolve'),
    path('feed-summary/', views.FeedSummaryView.as_view(), name='feed-summary'),
    path('daily-record-feed-summary/', views.DailyRecordFeedSummaryView.as_view(), name='daily-record-feed-summary'),
    path('feed-purchase-summary/', views.FeedPurchaseSummaryView.as_view(), name='feed-purchase-summary'),
    # Add this to your URL patterns
path('feed-consumption/<int:pk>/', views.FeedConsumptionDetailView.as_view(), name='feed-consumption-detail'),
        
    # Test endpoint
    path('test/', views.test_farm_view, name='test'),
]