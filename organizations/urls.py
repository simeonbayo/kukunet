# organizations/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'farmers', views.OrganizationFarmerViewSet, basename='organization-farmers')
router.register(r'projects', views.OrganizationProjectViewSet, basename='organization-projects')
router.register(r'members', views.OrganizationMemberViewSet, basename='organization-members')
router.register(r'partnerships', views.PartnershipViewSet, basename='organization-partnerships')

urlpatterns = [
    path('', include(router.urls)),
]