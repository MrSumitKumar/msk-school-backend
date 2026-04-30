from django.db.models import Q
from django.db import transaction
from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import StudentProfile
from .serializers import StudentProfileSerializer, StudentProfileCreateSerializer
from accounts.models import User
from accounts.serializers import UserCreateSerializer
from accounts.permissions import IsSuperAdmin, IsSchoolAdmin, IsTeacher, IsStudent, IsAdminOrTeacher, IsAdminUser
from accounts.soft_delete import SoftDeleteMixin
from academics.models import Section
from audit.services import log_action


class StudentListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        return StudentProfileCreateSerializer if self.request.method == 'POST' else StudentProfileSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsAdminOrTeacher()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        show_trash = self.request.query_params.get('trash') == 'true'
        
        if show_trash:
            qs = StudentProfile.objects.deleted_only()
        else:
            qs = StudentProfile.objects.all()

        # Multi-Tenant & RBAC Filtering
        if user.role == 'super_admin':
            pass # No filter for super_admin
        elif user.role == 'school_admin':
            qs = qs.filter(user__school=user.school)
        elif user.role == 'teacher':
            # Students in sections where teacher teaches a period OR is class teacher
            sections = Section.objects.filter(
                Q(periods__teacher=user) | 
                Q(class_teacher__user=user)
            ).distinct()
            qs = qs.filter(section__in=sections)
        elif user.role == 'student':
            qs = qs.filter(user=user)
        else:
            return StudentProfile.objects.none()

        # Additional filters
        grade = self.request.query_params.get('grade')
        section = self.request.query_params.get('section')
        search = self.request.query_params.get('search')
        if grade:
            qs = qs.filter(grade_id=grade)
        if section:
            qs = qs.filter(section_id=section)
        if search:
            qs = qs.filter(
                Q(user__first_name__icontains=search) | 
                Q(user__last_name__icontains=search) | 
                Q(admission_number__icontains=search)
            )
        return qs.select_related('user', 'grade', 'section', 'academic_session').distinct()


class StudentDetailView(generics.RetrieveUpdateDestroyAPIView):
    def get_serializer_class(self):
        return StudentProfileCreateSerializer if self.request.method in ['PUT','PATCH'] else StudentProfileSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdminOrTeacher()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        # Detail view should look into everything (active + deleted) to handle restore/permanent delete via this queryset if needed, 
        # but our specific views below will handle it better. 
        # For RetrieveUpdateDestroy, we want to return 404 for deleted items unless specifically asked? 
        # Requirement 6: If is_deleted=True -> return 404/403.
        qs = StudentProfile.objects.all()

        if user.role == 'super_admin':
            pass
        elif user.role == 'school_admin':
            qs = qs.filter(user__school=user.school)
        elif user.role == 'teacher':
            sections = Section.objects.filter(
                Q(periods__teacher=user) | 
                Q(class_teacher__user=user)
            ).distinct()
            qs = qs.filter(section__in=sections)
        elif user.role == 'student':
            qs = qs.filter(user=user)
        else:
            return StudentProfile.objects.none()
            
        return qs.select_related('user').distinct()

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            self.request, 'UPDATE', 'Student', instance.id, instance.user.full_name,
            f"Updated student: {instance.user.full_name} (ID: {instance.id})"
        )

    def perform_destroy(self, instance):
        instance.delete()
        log_action(
            self.request, 'SOFT_DELETE', 'Student', instance.id, instance.user.full_name,
            f"Soft-deleted student: {instance.user.full_name} (ID: {instance.id})"
        )


class CreateStudentWithUserView(APIView):
    """Create User + StudentProfile in one request"""
    def get_permissions(self):
        return [IsAuthenticated(), IsAdminOrTeacher()]

    def post(self, request):
        user_data = request.data.get('user', {})
        profile_data = request.data.get('profile', {})

        # Prevent role escalation & ensure tenant safety
        user_data['role'] = 'student'
        if request.user.role != 'super_admin':
            user_data['school'] = request.user.school_id
        elif not user_data.get('school'):
            return Response({'error': 'Super Admin must provide a school_id'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            with transaction.atomic():
                from schools.models import School
                school_id = user_data.get('school')
                if school_id:
                    school = School.objects.get(id=school_id)
                    subscription = getattr(school, 'active_subscription', None)
                    if subscription and subscription.is_active:
                        max_students = subscription.plan.max_students
                        if max_students > 0:
                            current_count = StudentProfile.objects.filter(user__school_id=school_id).count()
                            if current_count >= max_students:
                                return Response({'error': f'Student limit reached ({max_students}). Upgrade your plan.'}, status=status.HTTP_400_BAD_REQUEST)

                user_serializer = UserCreateSerializer(data=user_data)
                if not user_serializer.is_valid():
                    return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                user = user_serializer.save()
                
                profile_data['user'] = user.id
                profile_serializer = StudentProfileCreateSerializer(data=profile_data)
                if not profile_serializer.is_valid():
                    # Raising an exception here will trigger a rollback of the user creation
                    raise ValueError(profile_serializer.errors)
                
                profile = profile_serializer.save()
                
                # Audit logging (non-blocking thanks to on_commit)
                log_action(
                    request, 'CREATE', 'Student', profile.id, user.full_name,
                    f"Created student: {user.full_name} (ID: {profile.id})"
                )

                return Response({
                    'user': user_serializer.data,
                    'profile': profile_serializer.data
                }, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(e.args[0], status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            print(f"--- Student Creation Error ---\n{traceback.format_exc()}")
            return Response({'error': f"{type(e).__name__}: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StudentRestoreView(APIView):
    def get_permissions(self):
        return [IsAuthenticated(), IsAdminOrTeacher()]

    def post(self, request, pk):
        try:
            with transaction.atomic():
                # specifically use everything() to find deleted record
                student = StudentProfile.objects.everything().get(pk=pk)
                # School admin check
                if request.user.role == 'school_admin' and student.user.school != request.user.school:
                    return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
                
                student.restore()
                log_action(
                    request, 'RESTORE', 'Student', student.id, student.user.full_name,
                    f"Restored student: {student.user.full_name} (ID: {student.id})"
                )
                return Response({'message': 'Student restored successfully'}, status=status.HTTP_200_OK)
        except StudentProfile.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)


class StudentPermanentDeleteView(APIView):
    def get_permissions(self):
        return [IsAuthenticated(), IsAdminUser()]

    def delete(self, request, pk):
        try:
            with transaction.atomic():
                # specifically use everything() to find deleted record
                student = StudentProfile.objects.everything().get(pk=pk)
                
                # School admin check
                if request.user.role == 'school_admin' and student.user.school_id != request.user.school_id:
                    return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

                user = student.user
                repr_name = user.full_name
                
                # Delete profile first (hard delete) to avoid CASCADE issues with SoftDeleteMixin
                student.permanent_delete()
                
                # Deleting the user will clear the rest
                user.delete()
                
                log_action(
                    request, 'PERMANENT_DELETE', 'Student', pk, repr_name,
                    f"Permanently deleted student: {repr_name} (ID: {pk})"
                )
                
                return Response({'message': 'Student and associated account permanently deleted'}, status=status.HTTP_200_OK)
        except StudentProfile.DoesNotExist:
            return Response({'error': 'Student not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
