from rest_framework import serializers
from .models import AcademicSession, Grade, Section, Subject, GradeSubject, Book, Period


class AcademicSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicSession
        fields = '__all__'
        read_only_fields = ('school',)


class SectionSerializer(serializers.ModelSerializer):
    class_teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = Section
        fields = '__all__'

    def get_class_teacher_name(self, obj):
        return obj.class_teacher.user.full_name if obj.class_teacher else None


import re

class GradeSerializer(serializers.ModelSerializer):
    sections = SectionSerializer(many=True, read_only=True)

    class Meta:
        model = Grade
        fields = '__all__'
        read_only_fields = ('school',)

    def validate(self, data):
        # Allow the default validation to pass first
        data = super().validate(data)
        
        # Calculate order based on name or level
        name = data.get('name', getattr(self.instance, 'name', ''))
        level = data.get('level', getattr(self.instance, 'level', ''))
        
        match = re.search(r'\d+', name)
        order = 100
        if match:
            num = int(match.group())
            if 1 <= num <= 12:
                order = num + 3
            else:
                order = num + 3
        else:
            name_lower = name.lower()
            if 'nursery' in name_lower: order = 1
            elif 'lkg' in name_lower: order = 2
            elif 'ukg' in name_lower: order = 3
            else:
                level_orders = {
                    'pre_primary': 1,
                    'primary': 4,
                    'middle': 9,
                    'secondary': 12,
                    'senior_secondary': 14,
                }
                order = level_orders.get(level, 100)
                
        data['order'] = order
        return data


class SubjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Subject
        fields = '__all__'
        read_only_fields = ('school',)


class GradeSubjectSerializer(serializers.ModelSerializer):
    subject_name = serializers.ReadOnlyField(source='subject.name')
    grade_name = serializers.ReadOnlyField(source='grade.name')
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = GradeSubject
        fields = '__all__'

    def get_teacher_name(self, obj):
        return obj.teacher.full_name if obj.teacher else None


class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = '__all__'


class PeriodSerializer(serializers.ModelSerializer):
    subject_name = serializers.ReadOnlyField(source='subject.name')
    teacher_name = serializers.SerializerMethodField()

    class Meta:
        model = Period
        fields = '__all__'

    def get_teacher_name(self, obj):
        return obj.teacher.full_name if obj.teacher else None
