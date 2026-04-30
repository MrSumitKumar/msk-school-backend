from django.urls import path
from . import views

urlpatterns = [
    path('sessions/', views.AcademicSessionListCreateView.as_view(), name='session-list'),
    path('sessions/<int:pk>/', views.AcademicSessionDetailView.as_view(), name='session-detail'),
    path('grades/', views.GradeListCreateView.as_view(), name='grade-list'),
    path('grades/bulk-create/', views.GradeBulkCreateView.as_view(), name='grade-bulk-create'),
    path('grades/<int:pk>/', views.GradeDetailView.as_view(), name='grade-detail'),
    path('sections/', views.SectionListCreateView.as_view(), name='section-list'),
    path('sections/<int:pk>/', views.SectionDetailView.as_view(), name='section-detail'),
    path('subjects/', views.SubjectListCreateView.as_view(), name='subject-list'),
    path('subjects/<int:pk>/', views.SubjectDetailView.as_view(), name='subject-detail'),
    path('grade-subjects/', views.GradeSubjectListCreateView.as_view(), name='grade-subject-list'),
    path('books/', views.BookListCreateView.as_view(), name='book-list'),
    path('periods/', views.PeriodListCreateView.as_view(), name='period-list'),
]
