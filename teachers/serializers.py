from rest_framework import serializers
from .models import TeacherProfile
from accounts.serializers import UserSerializer


class TeacherProfileSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    class_teacher_section = serializers.SerializerMethodField()
    is_class_teacher = serializers.SerializerMethodField()
    class_teacher_section_id = serializers.SerializerMethodField()
    class_teacher_grade_id = serializers.SerializerMethodField()

    class Meta:
        model = TeacherProfile
        fields = '__all__'

    def get_class_teacher_section(self, obj):
        try:
            if hasattr(obj, 'teaching_section'):
                section = obj.teaching_section
                if section:
                    grade_name = section.grade.name if section.grade else "N/A"
                    return f"Grade {grade_name} - Section {section.name}"
        except Exception:
            # Handle cases like MultipleObjectsReturned if OneToOne is violated in DB
            return "Multiple Sections Assigned (Error)"
        return None

    def get_is_class_teacher(self, obj):
        try:
            section = obj.teaching_section
            return section is not None
        except Exception:
            return False

    def get_class_teacher_section_id(self, obj):
        try:
            if hasattr(obj, 'teaching_section') and obj.teaching_section:
                return obj.teaching_section.id
        except Exception:
            pass
        return None

    def get_class_teacher_grade_id(self, obj):
        try:
            if hasattr(obj, 'teaching_section') and obj.teaching_section and obj.teaching_section.grade:
                return obj.teaching_section.grade.id
        except Exception:
            pass
        return None


class TeacherProfileCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherProfile
        fields = '__all__'


class TeacherProfileNestedSerializer(serializers.ModelSerializer):
    class_teacher_section = serializers.SerializerMethodField()
    is_class_teacher = serializers.SerializerMethodField()
    class_teacher_section_id = serializers.SerializerMethodField()
    class_teacher_grade_id = serializers.SerializerMethodField()

    class Meta:
        model = TeacherProfile
        exclude = ['user']

    def get_class_teacher_section(self, obj):
        try:
            if hasattr(obj, 'teaching_section'):
                section = obj.teaching_section
                if section:
                    grade_name = section.grade.name if section.grade else "N/A"
                    return f"Grade {grade_name} - Section {section.name}"
        except Exception:
            return "Multiple Sections Assigned (Error)"
        return None

    def get_is_class_teacher(self, obj):
        try:
            section = obj.teaching_section
            return section is not None
        except Exception:
            return False

    def get_class_teacher_section_id(self, obj):
        try:
            if hasattr(obj, 'teaching_section') and obj.teaching_section:
                return obj.teaching_section.id
        except Exception:
            pass
        return None

    def get_class_teacher_grade_id(self, obj):
        try:
            if hasattr(obj, 'teaching_section') and obj.teaching_section and obj.teaching_section.grade:
                return obj.teaching_section.grade.id
        except Exception:
            pass
        return None
