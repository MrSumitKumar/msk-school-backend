from rest_framework import serializers
from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    marked_by_name = serializers.SerializerMethodField()
    marked_by = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Attendance
        fields = '__all__'

    def get_student_name(self, obj):
        return obj.student.full_name

    def get_marked_by_name(self, obj):
        return obj.marked_by.full_name if obj.marked_by else None


class BulkAttendanceSerializer(serializers.Serializer):
    section = serializers.IntegerField()
    academic_session = serializers.IntegerField()
    date = serializers.DateField()
    records = serializers.ListField(
        child=serializers.DictField()
    )
