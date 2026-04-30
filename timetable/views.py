from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from accounts.permissions import GlobalTenantPermission
from .models import TimetableConfig, DailyActivity, PeriodSlot, TimetableEntry
from .serializers import (
    TimetableConfigSerializer, DailyActivitySerializer, 
    PeriodSlotSerializer, TimetableEntrySerializer
)

class TimetableBaseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, GlobalTenantPermission]

    def get_queryset(self):
        if self.request.user.role == 'super_admin':
            return self.model.objects.all()
        return self.model.objects.filter(school=self.request.user.school)

    def perform_create(self, serializer):
        serializer.save(school=self.request.user.school)

class TimetableConfigViewSet(TimetableBaseViewSet):
    model = TimetableConfig
    serializer_class = TimetableConfigSerializer

    def get_object(self):
        # Allow school admins to get/update their single config easily
        if self.request.user.role == 'super_admin':
            return super().get_object()
        config, created = TimetableConfig.objects.get_or_create(
            school=self.request.user.school,
            defaults={'start_time': '08:00:00', 'end_time': '14:00:00'}
        )
        return config

class DailyActivityViewSet(TimetableBaseViewSet):
    model = DailyActivity
    serializer_class = DailyActivitySerializer

class PeriodSlotViewSet(TimetableBaseViewSet):
    model = PeriodSlot
    serializer_class = PeriodSlotSerializer

class TimetableEntryViewSet(TimetableBaseViewSet):
    model = TimetableEntry
    serializer_class = TimetableEntrySerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        section_id = self.request.query_params.get('section')
        if section_id:
            queryset = queryset.filter(section_id=section_id)
        
        teacher_id = self.request.query_params.get('teacher')
        if teacher_id:
            queryset = queryset.filter(teacher_id=teacher_id)
            
        return queryset
