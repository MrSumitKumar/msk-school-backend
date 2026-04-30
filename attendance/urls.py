from django.urls import path
from . import views

urlpatterns = [
    path('', views.AttendanceListCreateView.as_view(), name='attendance-list'),
    path('bulk/', views.BulkAttendanceView.as_view(), name='attendance-bulk'),
    path('summary/<int:student_id>/', views.AttendanceSummaryView.as_view(), name='attendance-summary'),
]
