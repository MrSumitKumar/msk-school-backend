import time
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User


def new_timestamp():
    return int(time.time())


class UserSerializer(serializers.ModelSerializer):
    full_name = serializers.ReadOnlyField()
    school_name = serializers.SerializerMethodField()
    school_logo = serializers.SerializerMethodField()
    theme_preference = serializers.SerializerMethodField()
    android_app_url = serializers.SerializerMethodField()
    ios_app_url = serializers.SerializerMethodField()
    teacher_profile = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'last_name', 'full_name', 'phone',
            'role', 'school', 'school_name', 'school_logo', 'theme_preference', 
            'android_app_url', 'ios_app_url',
            'profile_picture', 'is_active', 'date_joined', 'teacher_profile'
        ]
        read_only_fields = ['date_joined']

    def get_school_name(self, obj):
        return obj.school.name if obj.school else None

    def get_school_logo(self, obj):
        if obj.school and obj.school.logo:
            # Add cache buster to logo URL too
            logo_url = obj.school.logo.url
            request = self.context.get('request')
            full_url = request.build_absolute_uri(logo_url) if request else logo_url
            return f"{full_url}?t={new_timestamp()}" if '?' not in full_url else f"{full_url}&t={new_timestamp()}"
        return None

    def get_theme_preference(self, obj):
        return obj.school.theme_preference if obj.school else 'dark'

    def get_android_app_url(self, obj):
        return obj.school.android_app_url if obj.school else None

    def get_ios_app_url(self, obj):
        return obj.school.ios_app_url if obj.school else None

    def get_teacher_profile(self, obj):
        if hasattr(obj, 'teacher_profile'):
            from teachers.serializers import TeacherProfileNestedSerializer
            return TeacherProfileNestedSerializer(obj.teacher_profile, context=self.context).data
        return None


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['full_name'] = user.full_name
        token['school_id'] = user.school_id
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        data['user'] = UserSerializer(self.user, context=self.context).data
        return data


class UserCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = [
            'email', 'password', 'first_name', 'last_name', 'phone', 'role', 'school'
        ]

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=6)
