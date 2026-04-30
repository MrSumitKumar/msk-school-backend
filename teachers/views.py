from django.db.models import Q
from django.db import transaction
from rest_framework import generics, status, filters
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import TeacherProfile
from .serializers import TeacherProfileSerializer, TeacherProfileCreateSerializer
from accounts.models import User
from accounts.serializers import UserCreateSerializer
from accounts.permissions import IsSuperAdmin, IsSchoolAdmin, IsTeacher, IsAdminOrTeacher, IsAdminUser
from audit.services import log_action


class TeacherListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        return TeacherProfileCreateSerializer if self.request.method == 'POST' else TeacherProfileSerializer

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsAdminUser()]
        # List access for generic authenticated users (limited by get_queryset)
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        show_trash = self.request.query_params.get('trash') == 'true'

        if show_trash:
            qs = TeacherProfile.objects.deleted_only()
        else:
            qs = TeacherProfile.objects.all()

        if user.role == 'super_admin':
            pass
        elif user.role == 'school_admin':
            qs = qs.filter(user__school=user.school)
        elif user.role == 'teacher':
            # Teachers can only see themselves in the list
            qs = qs.filter(user=user)
        else:
            # Students/Parents/Accountants etc restricted by default here
            return TeacherProfile.objects.none()

        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(Q(user__first_name__icontains=search) | Q(user__last_name__icontains=search))
        return qs.select_related('user').distinct()


class TeacherDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TeacherProfileSerializer

    def get_permissions(self):
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [IsAuthenticated(), IsAdminUser()]
        return [IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        # Look into everything for detail checks
        qs = TeacherProfile.objects.all()

        if user.role == 'super_admin':
            pass
        elif user.role == 'school_admin':
            qs = qs.filter(user__school=user.school)
        elif user.role in ['teacher']:
            qs = qs.filter(user=user)
        else:
            return TeacherProfile.objects.none()
            
        return qs.select_related('user').distinct()

    def perform_update(self, serializer):
        instance = serializer.save()
        log_action(
            self.request, 'UPDATE', 'Teacher', instance.id, instance.user.full_name,
            f"Updated teacher: {instance.user.full_name} (ID: {instance.id})"
        )


    def perform_destroy(self, instance):
        instance.delete()
        log_action(
            self.request, 'SOFT_DELETE', 'Teacher', instance.id, instance.user.full_name,
            f"Soft-deleted teacher: {instance.user.full_name} (ID: {instance.id})"
        )


class CreateTeacherWithUserView(APIView):
    """Create User + TeacherProfile in one request"""
    def get_permissions(self):
        return [IsAuthenticated(), IsAdminUser()]

    def post(self, request):
        user_data = request.data.get('user', {})
        profile_data = request.data.get('profile', {})

        # Prevent role escalation & ensure tenant safety
        user_data['role'] = 'teacher'
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
                        max_teachers = subscription.plan.max_teachers
                        if max_teachers > 0:
                            current_count = TeacherProfile.objects.filter(user__school_id=school_id).count()
                            if current_count >= max_teachers:
                                return Response({'error': f'Teacher limit reached ({max_teachers}). Upgrade your plan.'}, status=status.HTTP_400_BAD_REQUEST)

                user_serializer = UserCreateSerializer(data=user_data)
                if not user_serializer.is_valid():
                    return Response(user_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
                
                user = user_serializer.save()
                
                profile_data['user'] = user.id
                profile_serializer = TeacherProfileCreateSerializer(data=profile_data)
                if not profile_serializer.is_valid():
                    # Raising an exception here will trigger a rollback of the user creation
                    raise ValueError(profile_serializer.errors)
                
                profile = profile_serializer.save()
                
                # Audit logging (non-blocking thanks to on_commit)
                log_action(
                    request, 'CREATE', 'Teacher', profile.id, user.full_name,
                    f"Created teacher: {user.full_name} (ID: {profile.id})"
                )

                return Response({
                    'user': user_serializer.data,
                    'profile': profile_serializer.data
                }, status=status.HTTP_201_CREATED)

        except ValueError as e:
            return Response(e.args[0], status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            import traceback
            print(f"--- Teacher Creation Error ---\n{traceback.format_exc()}")
            return Response({'error': f"{type(e).__name__}: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TeacherRestoreView(APIView):
    def get_permissions(self):
        return [IsAuthenticated(), IsAdminOrTeacher()]

    def post(self, request, pk):
        try:
            with transaction.atomic():
                teacher = TeacherProfile.objects.everything().get(pk=pk)
                # School admin check
                if request.user.role == 'school_admin' and teacher.user.school != request.user.school:
                    return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)
                
                teacher.restore()
                log_action(
                    request, 'RESTORE', 'Teacher', teacher.id, teacher.user.full_name,
                    f"Restored teacher: {teacher.user.full_name} (ID: {teacher.id})"
                )
                return Response({'message': 'Teacher restored successfully'}, status=status.HTTP_200_OK)
        except TeacherProfile.DoesNotExist:
            return Response({'error': 'Teacher not found'}, status=status.HTTP_404_NOT_FOUND)


class TeacherPermanentDeleteView(APIView):
    def get_permissions(self):
        return [IsAuthenticated(), IsAdminUser()]

    def delete(self, request, pk):
        try:
            with transaction.atomic():
                # specifically use everything() to find deleted record
                teacher = TeacherProfile.objects.everything().get(pk=pk)
                
                # School admin check
                if request.user.role == 'school_admin' and teacher.user.school_id != request.user.school_id:
                    return Response({'error': 'Unauthorized'}, status=status.HTTP_403_FORBIDDEN)

                user = teacher.user
                repr_name = user.full_name
                
                # Delete profile first (hard delete) to avoid CASCADE issues with SoftDeleteMixin
                teacher.permanent_delete()
                
                # Deleting the user will clear the rest
                user.delete()
                
                log_action(
                    request, 'PERMANENT_DELETE', 'Teacher', pk, repr_name,
                    f"Permanently deleted teacher: {repr_name} (ID: {pk})"
                )
                
                return Response({'message': 'Teacher and associated account permanently deleted'}, status=status.HTTP_200_OK)
        except TeacherProfile.DoesNotExist:
            return Response({'error': 'Teacher not found'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


