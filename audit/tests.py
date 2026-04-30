from django.test import TransactionTestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from schools.models import School
from students.models import StudentProfile
from audit.models import AuditLog

User = get_user_model()

class AuditLogTest(TransactionTestCase):
    def setUp(self):
        self.school = School.objects.create(name="Log School")
        self.super_admin = User.objects.create_superuser(
            email="super@log.com", password="password123", role="super_admin",
            first_name="Super", last_name="Admin"
        )
        self.school_admin = User.objects.create_user(
            email="admin@log.com", password="password123", role="school_admin", school=self.school,
            first_name="School", last_name="Admin"
        )
        self.teacher = User.objects.create_user(
            email="teacher@log.com", password="password123", role="teacher", school=self.school,
            first_name="Test", last_name="Teacher"
        )
        self.client = APIClient()

    def test_student_creation_logs(self):
        self.client.force_authenticate(user=self.school_admin)
        data = {
            "user": {
                "email": "student@log.com",
                "first_name": "Log",
                "last_name": "Student",
                "password": "password123"
            },
            "profile": {
                "admission_number": "LOG001"
            }
        }
        response = self.client.post('/api/students/create-with-user/', data, format='json')
        self.assertEqual(response.status_code, 201)
        
        # Check if log was created
        log = AuditLog.objects.filter(action_type='CREATE', model_name='Student').first()
        self.assertIsNotNone(log)
        self.assertEqual(log.object_repr, "Log Student")
        self.assertEqual(log.user, self.school_admin)
        self.assertEqual(log.school, self.school)

    def test_audit_log_permissions(self):
        # Teacher should be denied
        self.client.force_authenticate(user=self.teacher)
        response = self.client.get('/api/audit-logs/')
        self.assertEqual(response.status_code, 200) # DRF list returns 200 but results should be empty for non-allowed roles in my implementation
        self.assertEqual(len(response.data['results']), 0)

        # Super admin sees all
        self.client.force_authenticate(user=self.super_admin)
        response = self.client.get('/api/audit-logs/')
        self.assertEqual(response.status_code, 200)

    def test_login_logout_logs(self):
        # Test Login
        data = {"email": "admin@log.com", "password": "password123"}
        response = self.client.post('/api/auth/login/', data)
        self.assertEqual(response.status_code, 200)
        
        log = AuditLog.objects.filter(action_type='LOGIN', user=self.school_admin).first()
        self.assertIsNotNone(log)

        # Test Logout
        self.client.force_authenticate(user=self.school_admin)
        response = self.client.post('/api/auth/logout/')
        self.assertEqual(response.status_code, 200)
        
        log = AuditLog.objects.filter(action_type='LOGOUT', user=self.school_admin).first()
        self.assertIsNotNone(log)
