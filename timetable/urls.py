from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TimetableConfigViewSet, DailyActivityViewSet, 
    PeriodSlotViewSet, TimetableEntryViewSet
)

router = DefaultRouter()
router.register(r'config', TimetableConfigViewSet, basename='timetable-config')
router.register(r'activities', DailyActivityViewSet, basename='timetable-activity')
router.register(r'slots', PeriodSlotViewSet, basename='timetable-slot')
router.register(r'entries', TimetableEntryViewSet, basename='timetable-entry')

urlpatterns = [
    path('', include(router.urls)),
]
