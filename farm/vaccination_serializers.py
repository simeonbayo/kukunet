# farm/vaccination_serializers.py
from rest_framework import serializers
from .models import VaccinationSchedule, FlockVaccinationSchedule


class VaccinationScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = VaccinationSchedule
        fields = '__all__'


class FlockVaccinationScheduleSerializer(serializers.ModelSerializer):
    vaccine_name = serializers.CharField(source='vaccine_template.vaccine_name', read_only=True)
    vaccine_type = serializers.CharField(source='vaccine_template.vaccine_type', read_only=True)
    week_number = serializers.IntegerField(source='vaccine_template.week_number', read_only=True)
    
    class Meta:
        model = FlockVaccinationSchedule
        fields = '__all__'