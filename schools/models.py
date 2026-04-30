import json
from django.db import models


class SubscriptionPlan(models.Model):
    PLAN_CHOICES = [('basic', 'Basic'), ('pro', 'Pro'), ('premium', 'Premium')]

    name = models.CharField(max_length=50, choices=PLAN_CHOICES, unique=True)
    max_students = models.IntegerField(default=200, help_text="0 for unlimited")
    max_teachers = models.IntegerField(default=20, help_text="0 for unlimited")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_months = models.IntegerField(default=1)
    features = models.TextField(default='{}', help_text="JSON formatted features")
    unlocked_modules = models.TextField(default='[]', help_text="JSON list of unlocked modules like ['fees', 'exams']")

    def __str__(self):
        return self.name

class School(models.Model):
    BOARD_CHOICES = [
        ('cbse', 'CBSE'),
        ('icse', 'ICSE'),
        ('up_board', 'UP Board'),
        ('state', 'State Board'),
        ('ib', 'IB'),
        ('custom', 'Custom'),
    ]

    GRADING_CHOICES = [('CGPA', 'CGPA'), ('Percentage', 'Percentage')]
    THEME_CHOICES = [('light', 'Light'), ('dark', 'Dark')]

    name = models.CharField(max_length=200)
    board_type = models.CharField(max_length=20, choices=BOARD_CHOICES, default='cbse')
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=100, blank=True)
    pincode = models.CharField(max_length=10, blank=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    logo = models.ImageField(upload_to='school_logos/', null=True, blank=True)
    website = models.URLField(blank=True)
    
    # New Settings Fields
    principal_name = models.CharField(max_length=200, blank=True)
    school_code = models.CharField(max_length=50, blank=True)
    academic_year = models.CharField(max_length=20, default='2024-25')
    grading_system = models.CharField(max_length=20, choices=GRADING_CHOICES, default='Percentage')
    timezone = models.CharField(max_length=100, default='Asia/Kolkata')
    currency = models.CharField(max_length=10, default='INR')
    theme_preference = models.CharField(max_length=10, choices=THEME_CHOICES, default='dark')
    
    # Mobile App Links
    android_app_url = models.URLField(blank=True, null=True)
    ios_app_url = models.URLField(blank=True, null=True)

    subscription_plan = models.ForeignKey(
        SubscriptionPlan, on_delete=models.SET_NULL, null=True, blank=True
    )
    subscription_start = models.DateField(null=True, blank=True)
    subscription_end = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

    def get_subscription_features(self):
        plan = None
        active_sub = getattr(self, 'active_subscription', None)
        if active_sub and active_sub.plan:
            plan = active_sub.plan
        elif self.subscription_plan:
            plan = self.subscription_plan

        features = getattr(plan, 'features', '{}')
        if isinstance(features, str):
            try:
                features = json.loads(features)
            except json.JSONDecodeError:
                features = {}

        return features or {}

    def has_feature(self, feature_name):
        return bool(self.get_subscription_features().get(feature_name, False))

class Subscription(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('expired', 'Expired'),
        ('trial', 'Trial'),
        ('cancelled', 'Cancelled')
    ]
    school = models.OneToOneField(School, on_delete=models.CASCADE, related_name='active_subscription')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trial')
    trial_end_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.school.name} - {self.plan.name if self.plan else 'No Plan'}"

class Payment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded')
    ]
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='payments')
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=50) # 'razorpay', 'stripe'
    transaction_id = models.CharField(max_length=100, unique=True, null=True, blank=True)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_date = models.DateTimeField(auto_now_add=True)
    invoice_number = models.CharField(max_length=50, unique=True, null=True, blank=True)

    def __str__(self):
        return f"{self.school.name} - {self.amount} - {self.payment_status}"

class Invoice(models.Model):
    payment = models.OneToOneField(Payment, on_delete=models.CASCADE, related_name='invoice')
    invoice_number = models.CharField(max_length=50, unique=True)
    school_name = models.CharField(max_length=255)
    plan_name = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField()
    status = models.CharField(max_length=20, default='paid')
    pdf_file = models.FileField(upload_to='invoices/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.invoice_number

class Notification(models.Model):
    TYPE_CHOICES = [
        ('warning', 'Warning'),
        ('info', 'Info'),
        ('billing', 'Billing'),
        ('error', 'Error')
    ]
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='notifications')
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='info')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.school.name} - {self.notification_type}"

class Branch(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    city = models.CharField(max_length=100, blank=True)
    branch_code = models.CharField(max_length=50, unique=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.school.name} - {self.name}"
