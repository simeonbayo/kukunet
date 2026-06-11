# trainings/serializers.py
from rest_framework import serializers
from .models import Training, TrainingAttendance, TrainingEvaluation
from accounts.models import User

class TrainingSerializer(serializers.ModelSerializer):
    farmer_names = serializers.SerializerMethodField()
    farmer_count = serializers.SerializerMethodField()
    duration_days = serializers.IntegerField(read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    training_type_display = serializers.CharField(source='get_training_type_display', read_only=True)
    
    class Meta:
        model = Training
        fields = [
            'id', 'title', 'training_type', 'training_type_display', 'description',
            'topics_covered', 'start_date', 'end_date', 'start_time', 'end_time',
            'venue', 'district', 'village', 'gps_coordinates', 'trainer_name',
            'trainer_contact', 'trainer_email', 'trainer_organization',
            'expected_participants', 'actual_participants', 'farmers', 'farmer_names', 'farmer_count',
            'materials_provided', 'budget', 'actual_cost', 'status', 'status_display',
            'notes', 'feedback_summary', 'average_rating', 'duration_days',
            'created_at', 'updated_at', 'created_by', 'tenant'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'duration_days', 
                           'status_display', 'training_type_display', 'farmer_names', 'farmer_count']
        extra_kwargs = {
            'farmers': {'required': False, 'allow_empty': True},
            'tenant': {'required': False},
            'description': {'required': False, 'allow_blank': True},
            'district': {'required': False, 'allow_blank': True},
            'village': {'required': False, 'allow_blank': True},
            'gps_coordinates': {'required': False, 'allow_blank': True},
            'trainer_contact': {'required': False, 'allow_blank': True},
            'trainer_email': {'required': False, 'allow_blank': True},
            'trainer_organization': {'required': False, 'allow_blank': True},
            'materials_provided': {'required': False, 'allow_blank': True},
            'budget': {'required': False, 'allow_null': True},
            'actual_cost': {'required': False, 'allow_null': True},
            'notes': {'required': False, 'allow_blank': True},
            'feedback_summary': {'required': False, 'allow_blank': True},
            'average_rating': {'required': False, 'allow_null': True},
            'actual_participants': {'required': False, 'allow_null': True},
        }
    
    def get_farmer_names(self, obj):
        return [f.full_name for f in obj.farmers.all()]
    
    def get_farmer_count(self, obj):
        return obj.farmers.count()
    
    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        return super().update(instance, validated_data)


class TrainingAttendanceSerializer(serializers.ModelSerializer):
    farmer_name = serializers.CharField(source='farmer.full_name', read_only=True)
    
    class Meta:
        model = TrainingAttendance
        fields = '__all__'
        read_only_fields = ['id']


class TrainingEvaluationSerializer(serializers.ModelSerializer):
    farmer_name = serializers.CharField(source='farmer.full_name', read_only=True)
    average_rating = serializers.SerializerMethodField()
    
    class Meta:
        model = TrainingEvaluation
        fields = '__all__'
        read_only_fields = ['id', 'created_at']
    
    def get_average_rating(self, obj):
        ratings = [obj.content_rating, obj.trainer_rating, obj.materials_rating, obj.venue_rating, obj.overall_rating]
        return sum(ratings) / len(ratings)