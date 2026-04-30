from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import AuditLog
from .serializers import AuditLogSerializer
from accounts.permissions import IsSuperAdmin, IsSchoolAdmin

class AuditLogListView(generics.ListAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        
        # Super Admin sees everything
        if user.role == 'super_admin':
            qs = AuditLog.objects.all()
        # School Admin sees only their school's logs
        elif user.role == 'school_admin':
            qs = AuditLog.objects.filter(school=user.school)
        else:
            # Teacher, Student, etc. have no access
            return AuditLog.objects.none()

        # Filtering
        action_type = self.request.query_params.get('action_type')
        date_from = self.request.query_params.get('date_from')
        date_to = self.request.query_params.get('date_to')
        school_id = self.request.query_params.get('school')
        user_id = self.request.query_params.get('user')
        model_name = self.request.query_params.get('model_name')
        search = self.request.query_params.get('search')

        if action_type:
            qs = qs.filter(action_type=action_type)
        if date_from:
            qs = qs.filter(timestamp__date__gte=date_from)
        if date_to:
            qs = qs.filter(timestamp__date__lte=date_to)
        if school_id and user.role == 'super_admin':
            qs = qs.filter(school_id=school_id)
        if user_id:
            qs = qs.filter(user_id=user_id)
        if model_name:
            qs = qs.filter(model_name=model_name)
        if search:
            qs = qs.filter(object_repr__icontains=search)

        return qs.select_related('user', 'school')

class AuditLogDetailView(generics.RetrieveAPIView):
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return AuditLog.objects.all()
        elif user.role == 'school_admin':
            return AuditLog.objects.filter(school=user.school)
        return AuditLog.objects.none()

class AuditLogDestroyView(generics.DestroyAPIView):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

class AuditLogBulkDestroyView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsSuperAdmin]

    def post(self, request):
        ids = request.data.get('ids', [])
        if not ids:
            return Response({'error': 'No IDs provided'}, status=status.HTTP_400_BAD_REQUEST)
        
        deleted_count, _ = AuditLog.objects.filter(id__in=ids).delete()
        
        return Response({
            'message': f'Successfully deleted {deleted_count} activity logs',
            'deleted_count': deleted_count
        }, status=status.HTTP_200_OK)
