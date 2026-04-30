from django.db.models import Q
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Attendance
from .serializers import AttendanceSerializer, BulkAttendanceSerializer
from accounts.models import User
from accounts.permissions import IsSuperAdmin, IsSchoolAdmin, IsTeacher, IsAdminOrTeacher
from academics.models import Section


class AttendanceListCreateView(generics.ListCreateAPIView):
    serializer_class = AttendanceSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsAdminOrTeacher()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        qs = Attendance.objects.all()

        if user.role == 'super_admin':
            pass
        elif user.role == 'school_admin':
            qs = qs.filter(student__school=user.school)
        elif user.role == 'teacher':
            # Attendance for sections where teacher is involved
            sections = Section.objects.filter(
                Q(periods__teacher=user) | 
                Q(class_teacher__user=user)
            ).distinct()
            qs = qs.filter(section__in=sections)
        elif user.role == 'student':
            qs = qs.filter(student=user)
        else:
            return Attendance.objects.none()

        section = self.request.query_params.get('section')
        date = self.request.query_params.get('date')
        student = self.request.query_params.get('student')
        if section:
            qs = qs.filter(section_id=section)
        if date:
            qs = qs.filter(date=date)
        if student:
            qs = qs.filter(student_id=student)
            
        return qs.select_related('student', 'section', 'academic_session').distinct()

    def _teacher_assigned_section(self, user):
        if user.role != 'teacher':
            return None

        teacher_profile = getattr(user, 'teacher_profile', None)
        if not teacher_profile:
            return None

        return getattr(teacher_profile, 'teaching_section', None)

    def perform_create(self, serializer):
        section = serializer.validated_data.get('section')
        student = serializer.validated_data.get('student')

        if self.request.user.role == 'teacher':
            assigned_section = self._teacher_assigned_section(self.request.user)
            if not assigned_section or assigned_section.id != getattr(section, 'id', None):
                raise PermissionDenied('You can only mark attendance for your own assigned class section.')
            if not student or getattr(student, 'student_profile', None) is None or student.student_profile.section_id != section.id:
                raise PermissionDenied('You can only mark attendance for a student in your assigned section.')

        serializer.save(marked_by=self.request.user)


class BulkAttendanceView(APIView):
    """Mark attendance for entire section at once - Only class teacher can mark for their own section"""
    def get_permissions(self):
        return [IsAuthenticated(), IsAdminOrTeacher()]

    def post(self, request):
        serializer = BulkAttendanceSerializer(data=request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            section_id = data['section']
            
            # Security check: Teacher can ONLY mark for their OWN assigned section (as class teacher)
            if request.user.role == 'teacher':
                if not Section.objects.filter(id=section_id, class_teacher__user=request.user).exists():
                    return Response({'error': 'You can only mark attendance for your own assigned class section.'}, status=status.HTTP_403_FORBIDDEN)
            elif request.user.role == 'school_admin':
                section = Section.objects.filter(id=section_id).first()
                if not section or section.grade.school != request.user.school:
                    return Response({'error': 'Unauthorized section'}, status=status.HTTP_403_FORBIDDEN)

            # Validate that every attendance record belongs to the requested section
            invalid_students = []
            for record in data['records']:
                student_id = record.get('student')
                if not student_id:
                    continue
                student = User.objects.filter(id=student_id, student_profile__section_id=section_id).first()
                if not student:
                    invalid_students.append(student_id)
            if invalid_students:
                return Response(
                    {'error': 'One or more students do not belong to the selected section.', 'invalid_student_ids': invalid_students},
                    status=status.HTTP_400_BAD_REQUEST
                )

            records = data['records']
            created, updated = 0, 0
            for record in records:
                obj, was_created = Attendance.objects.update_or_create(
                    student_id=record['student'],
                    date=data['date'],
                    defaults={
                        'section_id': section_id,
                        'academic_session_id': data['academic_session'],
                        'status': record.get('status', 'present'),
                        'marked_by': request.user,
                        'remarks': record.get('remarks', ''),
                    }
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            return Response({'created': created, 'updated': updated}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AttendanceSummaryView(APIView):
    """Get attendance % summary for a student"""
    permission_classes = [IsAuthenticated]

    def get(self, request, student_id):
        # Security check: Student can only see their own summary
        if request.user.role == 'student' and request.user.id != int(student_id):
            return Response({'error': 'Access denied to other student summary'}, status=status.HTTP_403_FORBIDDEN)
        
        # Teacher check: Can only see if they teach this student
        if request.user.role == 'teacher':
            # Simple check: is student in a section taught by teacher
            is_taught = User.objects.filter(
                id=student_id,
                student_profile__section__in=Section.objects.filter(
                    Q(periods__teacher=request.user) | Q(class_teacher__user=request.user)
                )
            ).exists()
            if not is_taught:
                return Response({'error': 'Access denied to this student'}, status=status.HTTP_403_FORBIDDEN)

        records = Attendance.objects.filter(student_id=student_id)
        total = records.count()
        present = records.filter(status__in=['present', 'late']).count()
        percentage = round((present / total * 100), 2) if total else 0
        return Response({
            'total_days': total, 'present_days': present,
            'absent_days': total - present, 'percentage': percentage
        })
