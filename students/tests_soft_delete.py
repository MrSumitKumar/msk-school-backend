from django.test import TestCase
from django.contrib.auth import get_user_model
from schools.models import School
from students.models import StudentProfile

User = get_user_model()

class SoftDeleteTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="Test School")
        self.user = User.objects.create_user(
            email="student@test.com",
            password="password123",
            first_name="Test",
            last_name="Student",
            school=self.school
        )
        self.student = StudentProfile.objects.create(
            user=self.user,
            admission_number="ADM001"
        )

    def test_soft_delete(self):
        # Verify initial state
        self.assertFalse(self.student.is_deleted)
        self.assertEqual(StudentProfile.objects.count(), 1)

        # Perform soft delete
        self.student.delete()
        self.student.refresh_from_db()

        self.assertTrue(self.student.is_deleted)
        # Default manager should exclude it
        self.assertEqual(StudentProfile.objects.count(), 0)
        # everything() manager should include it
        self.assertEqual(StudentProfile.objects.everything().count(), 1)

    def test_restore(self):
        self.student.delete()
        self.assertTrue(self.student.is_deleted)

        self.student.restore()
        self.assertFalse(self.student.is_deleted)
        self.assertEqual(StudentProfile.objects.count(), 1)

    def test_permanent_delete(self):
        self.student.permanent_delete()
        self.assertEqual(StudentProfile.objects.everything().count(), 0)

    def test_rbac_restore_unauthorized(self):
        # Student cannot restore themselves
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=self.user)
        self.student.delete()
        
        response = client.post(f'/api/students/{self.student.id}/restore/')
        # Students don't have IsAdminOrTeacher permission
        self.assertEqual(response.status_code, 403)

    def test_multi_tenant_isolation(self):
        # Create another school and student
        school2 = School.objects.create(name="Other School")
        user2 = User.objects.create_user(email="other@test.com", password="pw", school=school2)
        student2 = StudentProfile.objects.create(user=user2, admission_number="ADM002")
        student2.delete()

        # Auth as school1 admin
        admin1 = User.objects.create_user(email="admin1@test.com", password="pw", school=self.school, role="school_admin")
        from rest_framework.test import APIClient
        client = APIClient()
        client.force_authenticate(user=admin1)

        # Should only see their own school's trash
        response = client.get('/api/students/?trash=true')
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 0) # student1 not deleted yet
        
        self.student.delete()
        response = client.get('/api/students/?trash=true')
        results = response.data.get('results', response.data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['id'], self.student.id)

