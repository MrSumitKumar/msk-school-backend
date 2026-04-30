from django.urls import path
from . import views

urlpatterns = [
    path('', views.TeacherListCreateView.as_view(), name='teacher-list'),
    path('create-with-user/', views.CreateTeacherWithUserView.as_view(), name='teacher-create-with-user'),
    path('<int:pk>/', views.TeacherDetailView.as_view(), name='teacher-detail'),
    path('<int:pk>/restore/', views.TeacherRestoreView.as_view(), name='teacher-restore'),
    path('<int:pk>/permanent-delete/', views.TeacherPermanentDeleteView.as_view(), name='teacher-permanent-delete'),
]
