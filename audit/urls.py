from django.urls import path
from . import views

urlpatterns = [
    path('', views.AuditLogListView.as_view(), name='audit-log-list'),
    path('bulk-delete/', views.AuditLogBulkDestroyView.as_view(), name='audit-log-bulk-delete'),
    path('<uuid:pk>/', views.AuditLogDetailView.as_view(), name='audit-log-detail'),
    path('<uuid:pk>/delete/', views.AuditLogDestroyView.as_view(), name='audit-log-delete'),
]
