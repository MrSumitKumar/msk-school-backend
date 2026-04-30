from django.test import TestCase
from schools.models import School, SubscriptionPlan
from academics.models import Grade, Section

class SchoolSignalTest(TestCase):
    def setUp(self):
        # Create default plans needed for signals
        SubscriptionPlan.objects.get_or_create(
            name='basic',
            defaults={'price': 0, 'duration_months': 1, 'unlocked_modules': ['dashboard']}
        )
    def test_automatic_structure_creation(self):
        """
        Test that creating a new school automatically generates 
        15 grades and 3 sections per grade (45 total).
        """
        school = School.objects.create(
            name="Test International School",
            contact_email="test@school.com",
            contact_phone="1234567890"
        )

        # Assert 15 grades are created
        grades = Grade.objects.filter(school=school)
        self.assertEqual(grades.count(), 15)

        # Assert specific grades exist
        grade_names = list(grades.values_list('name', flat=True))
        self.assertIn("Nursery", grade_names)
        self.assertIn("LKG", grade_names)
        self.assertIn("UKG", grade_names)
        for i in range(1, 13):
            self.assertIn(str(i), grade_names)

        # Assert 3 sections per grade (15 * 3 = 45)
        sections = Section.objects.filter(grade__school=school)
        self.assertEqual(sections.count(), 45)

        # Assert sections A, B, C exist for each grade
        for grade in grades:
            grade_sections = list(grade.sections.values_list('name', flat=True))
            self.assertEqual(len(grade_sections), 3)
            self.assertIn("A", grade_sections)
            self.assertIn("B", grade_sections)
            self.assertIn("C", grade_sections)

    def test_idempotency_on_update(self):
        """
        Test that updating a school doesn't create duplicate grades/sections.
        """
        school = School.objects.create(
            name="Idempotency School",
            contact_email="idem@school.com",
            contact_phone="9876543210"
        )
        
        initial_grade_count = Grade.objects.filter(school=school).count()
        initial_section_count = Section.objects.filter(grade__school=school).count()
        
        # Update school
        school.address = "123 New Street"
        school.save()
        
        self.assertEqual(Grade.objects.filter(school=school).count(), initial_grade_count)
        self.assertEqual(Section.objects.filter(grade__school=school).count(), initial_section_count)

    def test_automatic_subscription_creation(self):
        """
        Test that creating a new school automatically generates 
         a trial subscription with the basic plan.
        """
        school = School.objects.create(
            name="Subscription Test School",
            contact_email="subtest@school.com",
            contact_phone="5556667777"
        )
        
        # Check if subscription was created
        from schools.models import Subscription
        sub = Subscription.objects.filter(school=school).first()
        self.assertIsNotNone(sub)
        self.assertEqual(sub.plan.name, 'basic')
        self.assertEqual(sub.status, 'trial')
        self.assertTrue(sub.is_active)
        
        # Check school sync
        self.assertEqual(school.subscription_plan.name, 'basic')
        self.assertIsNotNone(school.subscription_start)
        self.assertIsNotNone(school.subscription_end)
