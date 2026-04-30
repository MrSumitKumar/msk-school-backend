from datetime import date, timedelta

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import User
from academics.models import AcademicSession, Grade
from schools.models import School, SubscriptionPlan
from .models import FeeCategory, FeeStructure


class FeeManagementTests(TestCase):
    def setUp(self):
        self.basic_plan = SubscriptionPlan.objects.create(
            name='basic',
            max_students=100,
            max_teachers=10,
            price=0,
            duration_months=1,
            features='{}',
            unlocked_modules='["fees"]',
        )
        self.pro_plan = SubscriptionPlan.objects.create(
            name='pro',
            max_students=500,
            max_teachers=50,
            price=199.99,
            duration_months=1,
            features='{"allow_installments": true, "allow_discounts": true, "allow_penalties": false}',
            unlocked_modules='["fees"]',
        )
        self.premium_plan = SubscriptionPlan.objects.create(
            name='premium',
            max_students=0,
            max_teachers=0,
            price=399.99,
            duration_months=1,
            features='{"allow_installments": true, "allow_discounts": true, "allow_penalties": true}',
            unlocked_modules='["fees"]',
        )

        self.school_basic = School.objects.create(
            name='Basic School',
            contact_email='basic@example.com',
            contact_phone='1111111111',
        )
        self.school_basic.subscription_plan = self.basic_plan
        self.school_basic.save(update_fields=['subscription_plan'])
        self.school_basic.active_subscription.plan = self.basic_plan
        self.school_basic.active_subscription.save(update_fields=['plan'])

        self.school_pro = School.objects.create(
            name='Pro School',
            contact_email='pro@example.com',
            contact_phone='2222222222',
        )
        self.school_pro.subscription_plan = self.pro_plan
        self.school_pro.save(update_fields=['subscription_plan'])
        self.school_pro.active_subscription.plan = self.pro_plan
        self.school_pro.active_subscription.status = 'active'
        self.school_pro.active_subscription.save(update_fields=['plan', 'status'])

        self.school_premium = School.objects.create(
            name='Premium School',
            contact_email='premium@example.com',
            contact_phone='3333333333',
        )
        self.school_premium.subscription_plan = self.premium_plan
        self.school_premium.save(update_fields=['subscription_plan'])
        self.school_premium.active_subscription.plan = self.premium_plan
        self.school_premium.active_subscription.status = 'active'
        self.school_premium.active_subscription.save(update_fields=['plan', 'status'])

        self.pro_admin = User.objects.create_user(
            email='admin@pro.local',
            password='password123',
            first_name='Pro',
            last_name='Admin',
            role='school_admin',
            school=self.school_pro,
        )
        self.basic_admin = User.objects.create_user(
            email='admin@basic.local',
            password='password123',
            first_name='Basic',
            last_name='Admin',
            role='school_admin',
            school=self.school_basic,
        )
        self.premium_admin = User.objects.create_user(
            email='admin@premium.local',
            password='password123',
            first_name='Premium',
            last_name='Admin',
            role='school_admin',
            school=self.school_premium,
        )

        self.pro_student = User.objects.create_user(
            email='student@pro.local',
            password='password123',
            first_name='Pro',
            last_name='Student',
            role='student',
            school=self.school_pro,
        )

        self.category = FeeCategory.objects.create(
            school=self.school_pro,
            name='Tuition',
        )
        self.grade = Grade.objects.filter(school=self.school_pro).first()
        self.academic_session = AcademicSession.objects.filter(school=self.school_pro).first()

        self.client = APIClient()

    def test_basic_plan_blocks_installments(self):
        self.client.force_authenticate(user=self.basic_admin)
        category_basic = FeeCategory.objects.create(school=self.school_basic, name='Tuition')
        grade_basic = Grade.objects.filter(school=self.school_basic).first()
        session_basic = AcademicSession.objects.filter(school=self.school_basic).first()
        data = {
            'school': self.school_basic.id,
            'grade': grade_basic.id if grade_basic else None,
            'category': category_basic.id,
            'academic_session': session_basic.id,
            'amount': '1000.00',
            'frequency': 'monthly',
            'due_date': 10,
            'installments': 3,
        }
        response = self.client.post('/api/fees/structures/', data, format='json')
        self.assertEqual(response.status_code, 400)
        self.assertIn('installments', response.data)

    def test_pro_plan_allows_discount_and_installments(self):
        self.client.force_authenticate(user=self.pro_admin)
        data = {
            'school': self.school_pro.id,
            'grade': self.grade.id,
            'category': self.category.id,
            'academic_session': self.academic_session.id,
            'amount': '1000.00',
            'frequency': 'monthly',
            'due_date': 10,
            'installments': 3,
            'discount_percent': '10.00',
        }
        response = self.client.post('/api/fees/structures/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['installments'], 3)
        self.assertEqual(response.data['effective_amount'], '900.00')
        self.assertEqual(response.data['installment_amount'], '300.00')

    def test_premium_plan_allows_penalties(self):
        self.client.force_authenticate(user=self.premium_admin)
        premium_category = FeeCategory.objects.create(school=self.school_premium, name='Library')
        premium_grade = Grade.objects.filter(school=self.school_premium).first()
        premium_session = AcademicSession.objects.filter(school=self.school_premium).first()
        data = {
            'school': self.school_premium.id,
            'grade': premium_grade.id,
            'category': premium_category.id,
            'academic_session': premium_session.id,
            'amount': '2000.00',
            'frequency': 'yearly',
            'due_date': 15,
            'installments': 1,
            'late_fee_penalty_percent': '5.00',
        }
        response = self.client.post('/api/fees/structures/', data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['late_fee_penalty_percent'], '5.00')

    def test_payment_status_and_balance_tracking(self):
        self.client.force_authenticate(user=self.pro_admin)
        structure = FeeStructure.objects.create(
            school=self.school_pro,
            grade=self.grade,
            category=self.category,
            academic_session=self.academic_session,
            amount='1000.00',
            frequency='monthly',
            due_date=10,
        )
        payload = {
            'student': self.pro_student.id,
            'fee_structure': structure.id,
            'amount_paid': '500.00',
            'payment_date': date.today().isoformat(),
            'due_date': date.today().isoformat(),
            'payment_mode': 'cash',
        }
        response = self.client.post('/api/fees/payments/', payload, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'partial')
        self.assertEqual(float(response.data['balance_due']), 500.0)

        payload['amount_paid'] = '1000.00'
        full_response = self.client.post('/api/fees/payments/', payload, format='json')
        self.assertEqual(full_response.status_code, 201)
        self.assertEqual(full_response.data['status'], 'paid')
        self.assertEqual(float(full_response.data['balance_due']), 0.0)

    def test_installment_schedule_overdue_and_payment_linking(self):
        self.client.force_authenticate(user=self.pro_admin)
        structure = FeeStructure.objects.create(
            school=self.school_pro,
            grade=self.grade,
            category=self.category,
            academic_session=self.academic_session,
            amount='1000.00',
            frequency='monthly',
            due_date=10,
            installments=2,
        )
        yesterday = date.today() - timedelta(days=1)
        installment_data = {
            'student': self.pro_student.id,
            'fee_structure': structure.id,
            'installment_number': 1,
            'due_date': yesterday.isoformat(),
            'amount_due': '500.00',
            'discount_amount': '0.00',
            'penalty_amount': '0.00',
        }
        response = self.client.post('/api/fees/installments/', installment_data, format='json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['status'], 'overdue')
        installment_id = response.data['id']

        payment_data = {
            'student': self.pro_student.id,
            'fee_structure': structure.id,
            'installment': installment_id,
            'amount_paid': '500.00',
            'payment_date': date.today().isoformat(),
            'due_date': yesterday.isoformat(),
            'payment_mode': 'upi',
        }
        payment_response = self.client.post('/api/fees/payments/', payment_data, format='json')
        self.assertEqual(payment_response.status_code, 201)
        self.assertEqual(payment_response.data['status'], 'paid')
        self.assertEqual(float(payment_response.data['balance_due']), 0.0)

    def test_receipt_download_for_fee_payment(self):
        self.client.force_authenticate(user=self.pro_admin)
        structure = FeeStructure.objects.create(
            school=self.school_pro,
            grade=self.grade,
            category=self.category,
            academic_session=self.academic_session,
            amount='1500.00',
            frequency='monthly',
            due_date=10,
        )
        response = self.client.post('/api/fees/payments/', {
            'student': self.pro_student.id,
            'fee_structure': structure.id,
            'amount_paid': '1500.00',
            'payment_date': date.today().isoformat(),
            'due_date': date.today().isoformat(),
            'payment_mode': 'online',
            'transaction_id': 'TXN-RECEIPT-1',
        }, format='json')
        self.assertEqual(response.status_code, 201)
        payment_id = response.data['id']
        receipt = self.client.get(f'/api/fees/payments/{payment_id}/receipt/')
        self.assertEqual(receipt.status_code, 200)
        self.assertEqual(receipt['Content-Type'], 'application/pdf')
        self.assertIn('attachment; filename', receipt['Content-Disposition'])

    def test_duplicate_transaction_id_is_rejected(self):
        self.client.force_authenticate(user=self.pro_admin)
        structure = FeeStructure.objects.create(
            school=self.school_pro,
            grade=self.grade,
            category=self.category,
            academic_session=self.academic_session,
            amount='1000.00',
            frequency='monthly',
            due_date=10,
        )
        payload = {
            'student': self.pro_student.id,
            'fee_structure': structure.id,
            'amount_paid': '500.00',
            'payment_date': date.today().isoformat(),
            'due_date': date.today().isoformat(),
            'payment_mode': 'upi',
            'transaction_id': 'TXN-DUP-123',
        }
        first = self.client.post('/api/fees/payments/', payload, format='json')
        self.assertEqual(first.status_code, 201)
        second = self.client.post('/api/fees/payments/', payload, format='json')
        self.assertEqual(second.status_code, 400)
        self.assertIn('transaction_id', second.data)

    def test_fee_payment_deletion(self):
        self.client.force_authenticate(user=self.pro_admin)
        structure = FeeStructure.objects.create(
            school=self.school_pro,
            grade=self.grade,
            category=self.category,
            academic_session=self.academic_session,
            amount='500.00',
            frequency='monthly',
            due_date=10,
        )
        create_resp = self.client.post('/api/fees/payments/', {
            'student': self.pro_student.id,
            'fee_structure': structure.id,
            'amount_paid': '500.00',
            'payment_date': date.today().isoformat(),
            'due_date': date.today().isoformat(),
            'payment_mode': 'cash',
        }, format='json')
        self.assertEqual(create_resp.status_code, 201)
        payment_id = create_resp.data['id']
        delete_resp = self.client.delete(f'/api/fees/payments/{payment_id}/')
        self.assertEqual(delete_resp.status_code, 204)
