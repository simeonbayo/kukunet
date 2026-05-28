from rest_framework import viewsets, generics, permissions
from .models import Course, Lesson, Enrollment, Certificate
from .serializers import (
    CourseSerializer, LessonSerializer, EnrollmentSerializer,
    CertificateSerializer, LessonProgressSerializer
)

class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseSerializer
    
    def get_queryset(self):
        queryset = Course.objects.filter(is_published=True)
        
        # Filter by category
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        
        # Filter by level
        level = self.request.query_params.get('level')
        if level:
            queryset = queryset.filter(level=level)
        
        return queryset

class MyEnrollmentsView(generics.ListAPIView):
    serializer_class = EnrollmentSerializer
    
    def get_queryset(self):
        return Enrollment.objects.filter(user=self.request.user).select_related('course')

class EnrollCourseView(generics.CreateAPIView):
    serializer_class = EnrollmentSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)