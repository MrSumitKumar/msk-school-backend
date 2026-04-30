from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import AcademicSession, Grade, Section, Subject, GradeSubject, Book, Period
from .serializers import (
    AcademicSessionSerializer, GradeSerializer, SectionSerializer,
    SubjectSerializer, GradeSubjectSerializer, BookSerializer, PeriodSerializer
)
from accounts.permissions import IsSuperAdmin, IsSchoolAdmin, IsTeacher, IsAdminOrTeacher, IsAdminUser


class AcademicSessionListCreateView(generics.ListCreateAPIView):
    serializer_class = AcademicSessionSerializer

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return AcademicSession.objects.all()
        return AcademicSession.objects.filter(school=user.school)

    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school)


class AcademicSessionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = AcademicSessionSerializer

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return AcademicSession.objects.all()
        return AcademicSession.objects.filter(school=user.school)


class GradeListCreateView(generics.ListCreateAPIView):
    serializer_class = GradeSerializer
    pagination_class = None

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return Grade.objects.all()
        return Grade.objects.filter(school=user.school)

    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school)


class GradeDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = GradeSerializer

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return Grade.objects.all()
        return Grade.objects.filter(school=user.school)


class SectionListCreateView(generics.ListCreateAPIView):
    serializer_class = SectionSerializer
    pagination_class = None

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Section.objects.all()
        if user.role != 'super_admin':
            qs = qs.filter(grade__school=user.school)
        
        grade = self.request.query_params.get('grade')
        if grade:
            qs = qs.filter(grade_id=grade)
        return qs


class SectionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SectionSerializer

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return Section.objects.all()
        return Section.objects.filter(grade__school=user.school)


class SubjectListCreateView(generics.ListCreateAPIView):
    serializer_class = SubjectSerializer
    pagination_class = None

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return Subject.objects.all()
        return Subject.objects.filter(school=user.school)

    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school)


class SubjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = SubjectSerializer

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return Subject.objects.all()
        return Subject.objects.filter(school=user.school)


class GradeSubjectListCreateView(generics.ListCreateAPIView):
    serializer_class = GradeSubjectSerializer

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = GradeSubject.objects.all()
        if user.role != 'super_admin':
            qs = qs.filter(grade__school=user.school)
        
        grade = self.request.query_params.get('grade')
        if grade:
            qs = qs.filter(grade_id=grade)
        return qs


class BookListCreateView(generics.ListCreateAPIView):
    serializer_class = BookSerializer

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return Book.objects.all()
        return Book.objects.filter(school=user.school)


class PeriodListCreateView(generics.ListCreateAPIView):
    serializer_class = PeriodSerializer

    def get_permissions(self):
        if self.request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Period.objects.all()
        if user.role != 'super_admin':
            qs = qs.filter(section__grade__school=user.school)
            
        section = self.request.query_params.get('section')
        if section:
            qs = qs.filter(section_id=section)
        day = self.request.query_params.get('day')
        if day:
            qs = qs.filter(day=day)
        return qs

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django.db import transaction

class GradeBulkCreateView(APIView):
    def get_permissions(self):
        return [IsAuthenticated(), IsAdminUser()]

    def post(self, request):
        user = request.user
        if not user.school:
            return Response({"error": "No school associated with user"}, status=status.HTTP_400_BAD_REQUEST)

        # Standard grade names from Nursery to 12th
        standard_grades = [
            # ('Name', 'Level', 'Order')
            ('Nursery', 'pre_primary', 1),
            ('LKG', 'pre_primary', 2),
            ('UKG', 'pre_primary', 3),
            ('1', 'primary', 4),
            ('2', 'primary', 5),
            ('3', 'primary', 6),
            ('4', 'primary', 7),
            ('5', 'primary', 8),
            ('6', 'middle', 9),
            ('7', 'middle', 10),
            ('8', 'middle', 11),
            ('9', 'secondary', 12),
            ('10', 'secondary', 13),
            ('11', 'senior_secondary', 14),
            ('12', 'senior_secondary', 15),
        ]

        try:
            with transaction.atomic():
                created_grades = 0
                created_sections = 0
                for name, level, order in standard_grades:
                    grade, created = Grade.objects.get_or_create(
                        school=user.school,
                        name=name,
                        defaults={'level': level, 'order': order}
                    )
                    if created:
                        created_grades += 1
                    
                    # Create sections A to F for each grade
                    for section_name in ['A', 'B', 'C', 'D', 'E', 'F']:
                        _, sec_created = Section.objects.get_or_create(
                            grade=grade,
                            name=section_name
                        )
                        if sec_created:
                            created_sections += 1
                
                return Response({
                    "message": f"Successfully setup {created_grades} grades and {created_sections} sections (A-F).",
                    "total_grades": Grade.objects.filter(school=user.school).count()
                }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"error": f"Failed to setup standard classes: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

