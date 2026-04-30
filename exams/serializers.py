from rest_framework import serializers
from .models import Exam, ExamSchedule, ExamResult, Question, ExamPaper, ExamPaperQuestion


class QuestionSerializer(serializers.ModelSerializer):
    subject_name = serializers.ReadOnlyField(source='subject.name')
    grade_name = serializers.ReadOnlyField(source='grade.name')
    created_by_name = serializers.ReadOnlyField(source='created_by.full_name')

    class Meta:
        model = Question
        fields = '__all__'


class QuestionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'


class ExamPaperQuestionSerializer(serializers.ModelSerializer):
    question_details = QuestionSerializer(source='question', read_only=True)

    class Meta:
        model = ExamPaperQuestion
        fields = '__all__'


class ExamPaperSerializer(serializers.ModelSerializer):
    questions = ExamPaperQuestionSerializer(many=True, read_only=True)
    subject_name = serializers.ReadOnlyField(source='subject.name')
    grade_name = serializers.ReadOnlyField(source='grade.name')
    exam_name = serializers.ReadOnlyField(source='exam.name')
    created_by_name = serializers.ReadOnlyField(source='created_by.full_name')

    class Meta:
        model = ExamPaper
        fields = '__all__'


class ExamPaperCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamPaper
        fields = '__all__'


class ExamPaperQuestionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExamPaperQuestion
        fields = '__all__'


class ExamScheduleSerializer(serializers.ModelSerializer):
    subject_name = serializers.ReadOnlyField(source='subject.name')
    class_name = serializers.ReadOnlyField(source='school_class.name')

    class Meta:
        model = ExamSchedule
        fields = '__all__'


class ExamSerializer(serializers.ModelSerializer):
    schedules = ExamScheduleSerializer(many=True, read_only=True)

    class Meta:
        model = Exam
        fields = '__all__'


class ExamResultSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    subject_name = serializers.ReadOnlyField(source='exam_schedule.subject.name')
    max_marks = serializers.ReadOnlyField(source='exam_schedule.max_marks')
    percentage = serializers.ReadOnlyField()
    is_pass = serializers.ReadOnlyField()

    class Meta:
        model = ExamResult
        fields = '__all__'

    def get_student_name(self, obj):
        return obj.student.full_name


class ExamResultUpdateSerializer(serializers.ModelSerializer):
    """Used for PUT/PATCH on a single result — only marks & remarks are editable"""
    percentage = serializers.ReadOnlyField()
    is_pass = serializers.ReadOnlyField()

    class Meta:
        model = ExamResult
        fields = ['id', 'marks_obtained', 'grade', 'remarks', 'percentage', 'is_pass']
