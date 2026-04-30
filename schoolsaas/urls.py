from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView
from accounts.views import LoginView, LogoutView

urlpatterns = [
    path('admin/', admin.site.urls),
    # Auth
    path('api/auth/login/', LoginView.as_view(), name='token_obtain_pair'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Apps
    path('api/accounts/', include('accounts.urls')),
    path('api/schools/', include('schools.urls')),
    path('api/academics/', include('academics.urls')),
    path('api/students/', include('students.urls')),
    path('api/teachers/', include('teachers.urls')),
    path('api/attendance/', include('attendance.urls')),
    path('api/fees/', include('fees.urls')),
    path('api/exams/', include('exams.urls')),
    path('api/timetable/', include('timetable.urls')),
    path('api/audit-logs/', include('audit.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
