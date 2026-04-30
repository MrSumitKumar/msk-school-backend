import json
from datetime import date
from decimal import Decimal

from django.db import models


class FeeCategory(models.Model):
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='fee_categories')
    name = models.CharField(max_length=100)  # Tuition, Bus, Library, etc.
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} - {self.school.name}"


class FeeStructure(models.Model):
    FREQUENCY_CHOICES = [
        ('monthly', 'Monthly'), ('quarterly', 'Quarterly'),
        ('half_yearly', 'Half Yearly'), ('yearly', 'Yearly'), ('one_time', 'One Time'),
    ]

    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='fee_structures')
    grade = models.ForeignKey('academics.Grade', on_delete=models.CASCADE, related_name='fee_structures', null=True)
    category = models.ForeignKey(FeeCategory, on_delete=models.CASCADE, related_name='structures')
    academic_session = models.ForeignKey(
        'academics.AcademicSession', on_delete=models.CASCADE, related_name='fee_structures'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES, default='monthly')
    due_date = models.IntegerField(default=10)   # Day of month
    installments = models.PositiveIntegerField(default=1)
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    late_fee_penalty_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    notes = models.TextField(blank=True)

    @property
    def effective_amount(self):
        discount_multiplier = Decimal(1) - (Decimal(self.discount_percent) / Decimal(100))
        return (self.amount * discount_multiplier).quantize(Decimal('0.01'))

    @property
    def installment_amount(self):
        if self.installments <= 1:
            return self.effective_amount
        return (self.effective_amount / self.installments).quantize(Decimal('0.01'))

    def __str__(self):
        grade_name = self.grade.name if self.grade else 'General'
        return f"{grade_name} - {self.category.name} - ₹{self.amount}"


class FeeInstallment(models.Model):
    STATUS_CHOICES = [
        ('paid', 'Paid'), ('pending', 'Pending'), ('overdue', 'Overdue'), ('partial', 'Partial'),
    ]

    student = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='fee_installments')
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE, related_name='fee_installment_records')
    installment_number = models.PositiveIntegerField(default=1)
    due_date = models.DateField()
    amount_due = models.DecimalField(max_digits=10, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    penalty_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'fee_structure', 'installment_number')
        ordering = ['fee_structure', 'installment_number']

    @property
    def total_due(self):
        return max(self.amount_due + self.penalty_amount - self.discount_amount, Decimal('0.00'))

    @property
    def balance_due(self):
        return max(self.total_due - self.amount_paid, Decimal('0.00'))

    def compute_status(self):
        if self.total_due > 0 and self.amount_paid >= self.total_due:
            return 'paid'
        if self.due_date < date.today():
            return 'overdue'
        if self.amount_paid > 0:
            return 'partial'
        return 'pending'

    def save(self, *args, **kwargs):
        self.status = self.compute_status()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.full_name} - Installment {self.installment_number} - ₹{self.amount_due} - {self.status}"


class FeePayment(models.Model):
    STATUS_CHOICES = [
        ('paid', 'Paid'), ('pending', 'Pending'), ('overdue', 'Overdue'), ('partial', 'Partial'),
    ]
    PAYMENT_MODE_CHOICES = [
        ('cash', 'Cash'), ('online', 'Online'), ('cheque', 'Cheque'), ('upi', 'UPI'),
    ]

    student = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='fee_payments')
    fee_structure = models.ForeignKey(FeeStructure, on_delete=models.CASCADE, related_name='payments')
    installment = models.ForeignKey(FeeInstallment, on_delete=models.SET_NULL, null=True, blank=True, related_name='payments')
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateField()
    due_date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    payment_mode = models.CharField(max_length=10, choices=PAYMENT_MODE_CHOICES, default='cash')
    transaction_id = models.CharField(max_length=100, blank=True)
    receipt_number = models.CharField(max_length=60, blank=True, null=True, unique=True)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    scholarship_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    late_fee_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    collected_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, related_name='collected_fees'
    )
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_due(self):
        total = self.amount_due + self.late_fee_amount - self.discount_amount - self.scholarship_amount
        return max(total, Decimal('0.00'))

    @property
    def balance_due(self):
        return max(self.total_due - self.amount_paid, Decimal('0.00'))

    def compute_status(self):
        if self.total_due > 0 and self.amount_paid >= self.total_due:
            return 'paid'
        if self.due_date < date.today() and self.amount_paid < self.total_due:
            return 'overdue'
        if self.amount_paid > 0 and self.amount_paid < self.total_due:
            return 'partial'
        return 'pending'

    def generate_receipt_number(self):
        if self.receipt_number:
            return self.receipt_number
        if self.pk:
            self.receipt_number = f"RCPT-{self.student.id:04d}-{self.id:06d}"
        else:
            self.receipt_number = f"RCPT-{self.student.id:04d}-TEMP"
        return self.receipt_number

    def save(self, *args, **kwargs):
        if self.installment is not None:
            self.amount_due = self.installment.total_due
            self.due_date = self.installment.due_date
        elif self.amount_due == 0 and self.fee_structure is not None:
            self.amount_due = self.fee_structure.installment_amount if self.fee_structure.installments > 1 else self.fee_structure.effective_amount

        self.status = self.compute_status()
        super().save(*args, **kwargs)

        if not self.receipt_number:
            self.generate_receipt_number()
            super().save(update_fields=['receipt_number'])

        if self.installment:
            paid_sum = self.installment.payments.exclude(pk=self.pk).aggregate(total=models.Sum('amount_paid'))['total'] or Decimal('0.00')
            self.installment.amount_paid = paid_sum + self.amount_paid
            self.installment.save()

    def __str__(self):
        return f"{self.student.full_name} - ₹{self.amount_paid} - {self.status}"
