from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from schools.models import School
from teachers.models import TeacherProfile

User = get_user_model()

class TeacherDeleteTest(TestCase):
    def setUp(self):
        self.school = School.objects.create(name="Test School")
        self.admin = User.objects.create_user(
            email="admin@test.com",
            password="password123",
            role="school_admin",
            school=self.school
        )
        self.teacher_user = User.objects.create_user(
            email="teacher@test.com",
            password="password123",
            role="teacher",
            school=self.school
        )
        self.teacher_profile = TeacherProfile.objects.create(
            user=self.teacher_user,
            employee_id="T001"
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_soft_delete_teacher(self):
        response = self.client.delete(f'/api/teachers/{self.teacher_profile.id}/')
        self.assertEqual(response.status_code, 204)
        self.teacher_profile.refresh_from_db()
        self.assertTrue(self.teacher_profile.is_deleted)
