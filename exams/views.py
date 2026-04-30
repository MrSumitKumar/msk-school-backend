from django.db.models import Q
from rest_framework import generics, status
from rest_framework.permissions import IsAuthenticated
from .models import Exam, ExamSchedule, ExamResult, Question, ExamPaper, ExamPaperQuestion
from .serializers import ExamSerializer, ExamScheduleSerializer, ExamResultSerializer, ExamResultUpdateSerializer, QuestionSerializer, QuestionCreateSerializer, ExamPaperSerializer, ExamPaperCreateSerializer, ExamPaperQuestionSerializer, ExamPaperQuestionCreateSerializer
from accounts.permissions import IsSuperAdmin, IsSchoolAdmin, IsSuperAdminOrSchoolAdmin, IsTeacher, IsAdminOrTeacher, GlobalTenantPermission
from academics.models import Section


class ExamListCreateView(generics.ListCreateAPIView):
    serializer_class = ExamSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsSuperAdminOrSchoolAdmin(), GlobalTenantPermission()]
        return [IsAuthenticated(), GlobalTenantPermission()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return Exam.objects.all()
        return Exam.objects.filter(school=user.school)


class ExamDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExamSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsSuperAdminOrSchoolAdmin(), GlobalTenantPermission()]
        return [IsAuthenticated(), GlobalTenantPermission()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return Exam.objects.all()
        return Exam.objects.filter(school=user.school)


class ExamScheduleListCreateView(generics.ListCreateAPIView):
    serializer_class = ExamScheduleSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsSuperAdminOrSchoolAdmin(), GlobalTenantPermission()]
        return [IsAuthenticated(), GlobalTenantPermission()]

    def get_queryset(self):
        user = self.request.user
        qs = ExamSchedule.objects.all()
        if user.role != 'super_admin':
            qs = qs.filter(exam__school=user.school)
            
        exam = self.request.query_params.get('exam')
        class_slug = self.request.query_params.get('class')
        if exam:
            qs = qs.filter(exam_id=exam)
        if class_slug:
            qs = qs.filter(school_class_id=class_slug)
        return qs


class ExamResultListCreateView(generics.ListCreateAPIView):
    serializer_class = ExamResultSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsAdminOrTeacher(), GlobalTenantPermission()]
        return [IsAuthenticated(), GlobalTenantPermission()]

    def get_queryset(self):
        user = self.request.user
        qs = ExamResult.objects.all()

        if user.role == 'super_admin':
            pass
        elif user.role == 'school_admin':
            qs = qs.filter(student__school=user.school)
        elif user.role == 'teacher':
             # Results for sections teacher is involved in
            sections = Section.objects.filter(
                Q(periods__teacher=user) | Q(class_teacher__user=user)
            ).distinct()
            qs = qs.filter(student__student_profile__section__in=sections)
        elif user.role == 'student':
            qs = qs.filter(student=user)
        else:
            return ExamResult.objects.none()

        student = self.request.query_params.get('student')
        schedule = self.request.query_params.get('exam_schedule')
        if student:
            qs = qs.filter(student_id=student)
        if schedule:
            qs = qs.filter(exam_schedule_id=schedule)
        return qs.select_related('student', 'exam_schedule__exam', 'exam_schedule__subject').distinct()


class ExamResultDetailView(generics.RetrieveUpdateDestroyAPIView):
    """GET/PUT/PATCH/DELETE a single exam result by ID"""
    serializer_class = ExamResultUpdateSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdminOrTeacher(), GlobalTenantPermission()]
        return [IsAuthenticated(), GlobalTenantPermission()]

    def get_queryset(self):
        user = self.request.user
        qs = ExamResult.objects.all()

        if user.role == 'super_admin':
            pass
        elif user.role == 'school_admin':
            qs = qs.filter(student__school=user.school)
        elif user.role == 'teacher':
            sections = Section.objects.filter(
                Q(periods__teacher=user) | Q(class_teacher__user=user)
            ).distinct()
            qs = qs.filter(student__student_profile__section__in=sections)
        elif user.role == 'student':
            qs = qs.filter(student=user)
        else:
            return ExamResult.objects.none()
            
        return qs.distinct()


# Question Management Views
class QuestionListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        return QuestionCreateSerializer if self.request.method == 'POST' else QuestionSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsAdminOrTeacher(), GlobalTenantPermission()]
        return [IsAuthenticated(), GlobalTenantPermission()]

    def get_queryset(self):
        user = self.request.user
        qs = Question.objects.filter(is_active=True)

        if user.role == 'super_admin':
            pass
        elif user.role == 'school_admin':
            qs = qs.filter(school=user.school)
        elif user.role == 'teacher':
            # Teachers can see questions they created or questions for subjects they teach
            sections = Section.objects.filter(
                Q(periods__teacher=user) | Q(class_teacher__user=user)
            ).distinct()
            grades = set()
            subjects = set()
            for section in sections:
                grades.add(section.grade)
                for period in section.periods.filter(teacher=user):
                    subjects.add(period.subject)
            qs = qs.filter(
                Q(created_by=user) |
                (Q(grade__in=grades) & Q(subject__in=subjects))
            )
        else:
            return Question.objects.none()

        # Filters
        subject = self.request.query_params.get('subject')
        grade = self.request.query_params.get('grade')
        question_type = self.request.query_params.get('question_type')
        difficulty = self.request.query_params.get('difficulty')

        if subject:
            qs = qs.filter(subject_id=subject)
        if grade:
            qs = qs.filter(grade_id=grade)
        if question_type:
            qs = qs.filter(question_type=question_type)
        if difficulty:
            qs = qs.filter(difficulty_level=difficulty)

        return qs.order_by('-created_at')


class QuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_serializer_class(self):
        return QuestionCreateSerializer if self.request.method in ['PUT', 'PATCH'] else QuestionSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdminOrTeacher(), GlobalTenantPermission()]
        return [IsAuthenticated(), GlobalTenantPermission()]

    def get_queryset(self):
        user = self.request.user
        qs = Question.objects.all()

        if user.role == 'super_admin':
            pass
        elif user.role == 'school_admin':
            qs = qs.filter(school=user.school)
        elif user.role == 'teacher':
            # Teachers can only edit questions they created
            qs = qs.filter(created_by=user)
        else:
            return Question.objects.none()

        return qs


# Exam Paper Management Views
class ExamPaperListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        return ExamPaperCreateSerializer if self.request.method == 'POST' else ExamPaperSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsAdminOrTeacher(), GlobalTenantPermission()]
        return [IsAuthenticated(), GlobalTenantPermission()]

    def get_queryset(self):
        user = self.request.user
        qs = ExamPaper.objects.all()

        if user.role == 'super_admin':
            pass
        elif user.role == 'school_admin':
            qs = qs.filter(exam__school=user.school)
        elif user.role == 'teacher':
            # Teachers can see papers they created or for subjects they teach
            sections = Section.objects.filter(
                Q(periods__teacher=user) | Q(class_teacher__user=user)
            ).distinct()
            grades = set()
            subjects = set()
            for section in sections:
                grades.add(section.grade)
                for period in section.periods.filter(teacher=user):
                    subjects.add(period.subject)
            qs = qs.filter(
                Q(created_by=user) |
                (Q(grade__in=grades) & Q(subject__in=subjects))
            )
        else:
            return ExamPaper.objects.none()

        # Filters
        exam = self.request.query_params.get('exam')
        subject = self.request.query_params.get('subject')
        grade = self.request.query_params.get('grade')

        if exam:
            qs = qs.filter(exam_id=exam)
        if subject:
            qs = qs.filter(subject_id=subject)
        if grade:
            qs = qs.filter(grade_id=grade)

        return qs.order_by('-created_at')


class ExamPaperDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_serializer_class(self):
        return ExamPaperCreateSerializer if self.request.method in ['PUT', 'PATCH'] else ExamPaperSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdminOrTeacher(), GlobalTenantPermission()]
        return [IsAuthenticated(), GlobalTenantPermission()]

    def get_queryset(self):
        user = self.request.user
        qs = ExamPaper.objects.all()

        if user.role == 'super_admin':
            pass
        elif user.role == 'school_admin':
            qs = qs.filter(exam__school=user.school)
        elif user.role == 'teacher':
            # Teachers can only edit papers they created
            qs = qs.filter(created_by=user)
        else:
            return ExamPaper.objects.none()

        return qs


# Exam Paper Question Management Views
class ExamPaperQuestionListCreateView(generics.ListCreateAPIView):
    serializer_class = ExamPaperQuestionCreateSerializer

    def get_permissions(self):
        return [IsAuthenticated(), IsAdminOrTeacher(), GlobalTenantPermission()]

    def get_queryset(self):
        user = self.request.user
        qs = ExamPaperQuestion.objects.all()

        if user.role == 'super_admin':
            pass
        elif user.role == 'school_admin':
            qs = qs.filter(exam_paper__exam__school=user.school)
        elif user.role == 'teacher':
            # Teachers can only manage questions in papers they created
            qs = qs.filter(exam_paper__created_by=user)
        else:
            return ExamPaperQuestion.objects.none()

        exam_paper = self.request.query_params.get('exam_paper')
        if exam_paper:
            qs = qs.filter(exam_paper_id=exam_paper)

        return qs.order_by('order')


class ExamPaperQuestionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = ExamPaperQuestionCreateSerializer

    def get_permissions(self):
        return [IsAuthenticated(), IsAdminOrTeacher(), GlobalTenantPermission()]

    def get_queryset(self):
        user = self.request.user
        qs = ExamPaperQuestion.objects.all()

        if user.role == 'super_admin':
            pass
        elif user.role == 'school_admin':
            qs = qs.filter(exam_paper__exam__school=user.school)
        elif user.role == 'teacher':
            # Teachers can only manage questions in papers they created
            qs = qs.filter(exam_paper__created_by=user)
        else:
            return ExamPaperQuestion.objects.none()

        return qs
