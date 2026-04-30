from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import get_user_model
from .serializers import CustomTokenObtainPairSerializer, UserSerializer, UserCreateSerializer, ChangePasswordSerializer
from .permissions import IsSuperAdmin, IsSchoolAdmin, IsSuperAdminOrSchoolAdmin

from audit.services import log_action

User = get_user_model()



class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]
    serializer_class = CustomTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        # ─── DEBUG LOGGING ──────────────────────────────
        email = request.data.get('email', '')
        password = request.data.get('password', '')
        print(f"DEBUG LOGIN: Email='{email}' (len={len(email)}), Password='{'*' * len(password)}' (len={len(password)})")
        # ────────────────────────────────────────────────
        try:
            response = super().post(request, *args, **kwargs)
        except Exception as e:
            print(f"DEBUG LOGIN ERROR: {str(e)}")
            return Response({'detail': 'Invalid credentials. Please try again.'}, status=status.HTTP_401_UNAUTHORIZED)

        if response.status_code == 200:
            email = request.data.get('email')
            try:
                user = User.objects.get(email=email)
                log_action(
                    request, 'LOGIN', 'User', user.id, user.full_name,
                    f"User logged in: {user.full_name} ({user.email})",
                    metadata={'role': user.role},
                    user_override=user
                )
            except User.DoesNotExist:
                pass
        return response


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        log_action(
            request, 'LOGOUT', 'User', user.id, user.full_name,
            f"User logged out: {user.full_name} ({user.email})"
        )
        return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)


class UserListCreateView(generics.ListCreateAPIView):
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer

    def get_permissions(self):
        # Restricted to admins
        return [IsAuthenticated(), IsSuperAdminOrSchoolAdmin()]

    def get_queryset(self):
        user = self.request.user
        qs = User.objects.all()
        if user.role == 'super_admin':
            pass
        elif user.role == 'school_admin':
            qs = qs.filter(school=user.school)
        else:
            return User.objects.none()

        role = self.request.query_params.get('role')
        if role:
            qs = qs.filter(role=role)
        return qs


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = UserSerializer

    def get_permissions(self):
        return [IsAuthenticated(), IsSuperAdminOrSchoolAdmin()]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return User.objects.all()
        return User.objects.filter(school=user.school)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # Force a fresh fetch of the user and their associated school from the DB
        # This bypasses any session/object caching causing "paku" to persist
        user = User.objects.select_related('school').get(id=request.user.id)
        serializer = UserSerializer(user, context={'request': request})
        
        response = Response(serializer.data)
        response['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        return response


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            if not user.check_password(serializer.validated_data['old_password']):
                return Response({'error': 'Invalid current password'}, status=status.HTTP_400_BAD_REQUEST)
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response({'message': 'Password changed successfully'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DashboardStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        if user.role == 'super_admin':
            from schools.models import School
            stats = {
                'total_schools': School.objects.count(),
                'active_schools': School.objects.filter(is_active=True).count(),
                'inactive_schools': School.objects.filter(is_active=False).count(),
                'total_users': User.objects.count(),
                'total_admins': User.objects.filter(role='school_admin').count(),
            }
        elif user.role == 'teacher':
            from attendance.models import Attendance
            from academics.models import Section
            school = user.school
            
            # Count students in sections taught by teacher or where teacher is class teacher
            from django.db.models import Q
            sections = Section.objects.filter(
                Q(periods__teacher=user) | Q(class_teacher__user=user)
            ).distinct()
            
            stats = {
                'total_students': User.objects.filter(student_profile__section__in=sections).count(),
                'assigned_sections': sections.count(),
                'attendance_marked_today': Attendance.objects.filter(
                    marked_by=user,
                    date=__import__('datetime').date.today()
                ).values('student').distinct().count(),
            }
        elif user.role == 'student':
            from attendance.models import Attendance
            from fees.models import FeePayment
            try:
                student_profile = user.student_profile
                total_att = Attendance.objects.filter(student=user).count()
                present_att = Attendance.objects.filter(student=user, status__in=['present', 'late']).count()
                stats = {
                    'attendance_percentage': round((present_att / total_att * 100), 1) if total_att else 0,
                    'pending_fees_count': FeePayment.objects.filter(student=user, status='pending').count(),
                    'roll_number': student_profile.roll_number,
                    'section': str(student_profile.section) if student_profile.section else '',
                    'class': str(student_profile.school_class) if student_profile.school_class else '',
                }
            except Exception:
                stats = {'attendance_percentage': 0, 'pending_fees_count': 0}
        else:
            # school_admin / accountant
            school = user.school
            from django.db.models import Sum, Q, Count
            
            from students.models import StudentProfile
            from teachers.models import TeacherProfile
            from fees.models import FeePayment
            from attendance.models import Attendance
            import datetime

            # Combined stats for better performance
            student_count = StudentProfile.objects.filter(user__school=school).count()
            teacher_count = TeacherProfile.objects.filter(user__school=school).count()
            
            # Use conditional aggregation to get fee stats in one query
            fee_stats = FeePayment.objects.filter(student__school=school).aggregate(
                total_collected=Sum('amount_paid', filter=Q(status='paid')),
                pending_count=Count('id', filter=Q(status='pending'))
            )
            
            attendance_today = Attendance.objects.filter(
                student__school=school,
                date=datetime.date.today()
            ).values('student').distinct().count()

            stats = {
                'total_students': student_count,
                'total_teachers': teacher_count,
                'school_name': school.name if school else '',
                'fees_collected': float(fee_stats['total_collected'] or 0),
                'fees_pending_count': fee_stats['pending_count'],
                'attendance_today': attendance_today,
            }
        return Response(stats)
