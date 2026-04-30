from rest_framework import serializers
from .models import AuditLog

class AuditLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.full_name', read_only=True)
    school_name = serializers.CharField(source='school.name', read_only=True)

    class Meta:
        model = AuditLog
        fields = [
            'id', 'timestamp', 'user', 'user_name', 'school', 'school_name',
            'action_type', 'model_name', 'object_id', 'object_repr',
            'description', 'ip_address', 'user_agent', 'metadata'
        ]
