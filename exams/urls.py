from django.urls import path
from . import views

urlpatterns = [
    path('', views.ExamListCreateView.as_view(), name='exam-list'),
    path('<int:pk>/', views.ExamDetailView.as_view(), name='exam-detail'),
    path('schedules/', views.ExamScheduleListCreateView.as_view(), name='exam-schedule-list'),
    path('results/', views.ExamResultListCreateView.as_view(), name='exam-result-list'),
    path('results/<int:pk>/', views.ExamResultDetailView.as_view(), name='exam-result-detail'),

    # Question Management
    path('questions/', views.QuestionListCreateView.as_view(), name='question-list'),
    path('questions/<int:pk>/', views.QuestionDetailView.as_view(), name='question-detail'),

    # Exam Paper Management
    path('papers/', views.ExamPaperListCreateView.as_view(), name='exam-paper-list'),
    path('papers/<int:pk>/', views.ExamPaperDetailView.as_view(), name='exam-paper-detail'),

    # Exam Paper Questions
    path('paper-questions/', views.ExamPaperQuestionListCreateView.as_view(), name='exam-paper-question-list'),
    path('paper-questions/<int:pk>/', views.ExamPaperQuestionDetailView.as_view(), name='exam-paper-question-detail'),
]
