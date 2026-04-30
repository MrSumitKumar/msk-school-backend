from rest_framework import serializers
from .models import TimetableConfig, DailyActivity, PeriodSlot, TimetableEntry

class TimetableConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = TimetableConfig
        fields = '__all__'
        read_only_fields = ['school']

class DailyActivitySerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyActivity
        fields = '__all__'
        read_only_fields = ['school']

class PeriodSlotSerializer(serializers.ModelSerializer):
    class Meta:
        model = PeriodSlot
        fields = '__all__'
        read_only_fields = ['school']

class TimetableEntrySerializer(serializers.ModelSerializer):
    section_name = serializers.ReadOnlyField(source='section.name')
    grade_name = serializers.ReadOnlyField(source='section.grade.name')
    subject_name = serializers.ReadOnlyField(source='subject.name')
    teacher_name = serializers.ReadOnlyField(source='teacher.get_full_name')
    slot_details = PeriodSlotSerializer(source='slot', read_only=True)

    class Meta:
        model = TimetableEntry
        fields = '__all__'
        read_only_fields = ['school']

    def validate(self, attrs):
        school = self.context['request'].user.school
        day = attrs.get('day')
        slot = attrs.get('slot')
        teacher = attrs.get('teacher')
        section = attrs.get('section')

        # 1. Teacher Conflict Check
        teacher_conflict = TimetableEntry.objects.filter(
            school=school,
            day=day,
            slot=slot,
            teacher=teacher
        )
        
        if self.instance:
            teacher_conflict = teacher_conflict.exclude(id=self.instance.id)
            
        if teacher_conflict.exists():
            conflict = teacher_conflict.first()
            raise serializers.ValidationError({
                "teacher": f"Teacher {teacher.get_full_name()} is already assigned to {conflict.section} at this time."
            })

        # 2. Section Conflict Check (redundant due to unique_together but good for UX)
        section_conflict = TimetableEntry.objects.filter(
            school=school,
            day=day,
            slot=slot,
            section=section
        )

        if self.instance:
            section_conflict = section_conflict.exclude(id=self.instance.id)

        if section_conflict.exists():
            raise serializers.ValidationError({
                "slot": f"This section already has a subject assigned for this period."
            })

        return attrs
