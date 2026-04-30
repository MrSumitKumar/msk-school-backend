from rest_framework import serializers
from .models import StudentProfile
from accounts.serializers import UserSerializer


class StudentProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    grade_name = serializers.ReadOnlyField(source='grade.name')
    section_name = serializers.ReadOnlyField(source='section.name')

    class Meta:
        model = StudentProfile
        fields = '__all__'


class StudentProfileCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentProfile
        fields = '__all__'
