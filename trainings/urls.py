# trainings/urls.py
from django.urls import path
from .views import (
    TrainingListView,
    TrainingDetailView,
    TrainingAttendanceView,
    TrainingEvaluationView,
    TrainingStatusUpdateView 
)

urlpatterns = [
    path('api/v1/organization/trainings/', TrainingListView.as_view(), name='trainings'),
    path('api/v1/organization/trainings/<int:training_id>/', TrainingDetailView.as_view(), name='training-detail'),
    path('api/v1/organization/trainings/<int:training_id>/status/', TrainingStatusUpdateView.as_view(), name='training-status-update'),
    path('api/v1/organization/trainings/<int:training_id>/attendance/', TrainingAttendanceView.as_view(), name='training-attendance'),
    path('api/v1/organization/trainings/<int:training_id>/evaluate/', TrainingEvaluationView.as_view(), name='training-evaluate'),
]