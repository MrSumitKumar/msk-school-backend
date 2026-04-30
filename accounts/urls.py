from django.urls import path
from . import views
from rest_framework_simplejwt.views import TokenRefreshView # Assuming this import is needed for TokenRefreshView

urlpatterns = [
    path('users/', views.UserListCreateView.as_view(), name='user-list'),
    path('users/<int:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('me/', views.MeView.as_view(), name='me'),
    path('dashboard-stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
]
