from django.urls import path
from . import views

urlpatterns = [
    path('', views.StudentListCreateView.as_view(), name='student-list'),
    path('<int:pk>/', views.StudentDetailView.as_view(), name='student-detail'),
    path('<int:pk>/restore/', views.StudentRestoreView.as_view(), name='student-restore'),
    path('<int:pk>/permanent-delete/', views.StudentPermanentDeleteView.as_view(), name='student-permanent-delete'),
    path('create-with-user/', views.CreateStudentWithUserView.as_view(), name='create-student-with-user'),
]
