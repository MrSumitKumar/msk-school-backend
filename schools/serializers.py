from rest_framework import serializers
import json
from .models import School, SubscriptionPlan, Subscription, Payment, Invoice, Notification, Branch


class SubscriptionPlanSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubscriptionPlan
        fields = '__all__'

    def to_internal_value(self, data):
        # Coerce JSON fields from JS arrays/objects to strings
        if 'unlocked_modules' in data and isinstance(data['unlocked_modules'], list):
            data['unlocked_modules'] = json.dumps(data['unlocked_modules'])
        if 'features' in data and isinstance(data['features'], (list, dict)):
            data['features'] = json.dumps(data['features'])
        if 'unlocked_modules' not in data:
            data['unlocked_modules'] = '[]'
        if 'features' not in data:
            data['features'] = '{}'
        return super().to_internal_value(data)

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Parse JSON text fields back to Python objects for API consumers
        if isinstance(data.get('unlocked_modules'), str):
            try:
                data['unlocked_modules'] = json.loads(data['unlocked_modules'])
            except json.JSONDecodeError:
                data['unlocked_modules'] = []
        if isinstance(data.get('features'), str):
            try:
                data['features'] = json.loads(data['features'])
            except json.JSONDecodeError:
                data['features'] = {}
        return data

    def validate_price(self, value):
        if value <= 0:
            raise serializers.ValidationError("Price must be greater than 0")
        return value


class SchoolSerializer(serializers.ModelSerializer):
    subscription_plan_name = serializers.SerializerMethodField()
    total_students = serializers.SerializerMethodField()
    total_teachers = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()
    owner_email = serializers.SerializerMethodField()
    subscription_details = serializers.SerializerMethodField()

    class Meta:
        model = School
        fields = '__all__'

    def get_subscription_plan_name(self, obj):
        return obj.subscription_plan.name if obj.subscription_plan else None

    def get_total_students(self, obj):
        return obj.users.filter(role='student').count()

    def get_total_teachers(self, obj):
        return obj.users.filter(role='teacher').count()

    def get_owner(self, obj):
        owner = obj.users.filter(role='school_admin').first()
        return owner.full_name if owner else None

    def get_owner_email(self, obj):
        owner = obj.users.filter(role='school_admin').first()
        return owner.email if owner else None

    def get_subscription_details(self, obj):
        sub = getattr(obj, 'active_subscription', None)
        if sub:
            return {
                'id': sub.id,
                'plan_id': sub.plan_id,
                'plan_name': sub.plan.name if sub.plan else None,
                'start_date': sub.start_date,
                'end_date': sub.end_date,
                'status': sub.status,
                'is_active': sub.is_active,
            }
        return None


class SchoolCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = '__all__'

class SchoolSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = School
        fields = [
            'name', 'board_type', 'address', 'city', 'state', 'pincode',
            'contact_email', 'contact_phone', 'logo', 'website',
            'principal_name', 'school_code', 'academic_year',
            'grading_system', 'timezone', 'currency', 'theme_preference',
            'android_app_url', 'ios_app_url'
        ]

    def validate_contact_phone(self, value):
        if value and not value.replace('+', '').replace('-', '').isdigit():
            raise serializers.ValidationError("Invalid phone number format.")
        return value

class SubscriptionSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)
    plan_name = serializers.CharField(source='plan.name', read_only=True)
    plan_details = SubscriptionPlanSerializer(source='plan', read_only=True)
    school_owner = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = '__all__'

    def get_school_owner(self, obj):
        owner = obj.school.users.filter(role='school_admin').first()
        return owner.full_name if owner else None

class PaymentSerializer(serializers.ModelSerializer):
    school_name = serializers.CharField(source='school.name', read_only=True)
    plan_name = serializers.CharField(source='plan.name', read_only=True)

    class Meta:
        model = Payment
        fields = ['id', 'school', 'school_name', 'plan', 'plan_name', 'amount', 'payment_method', 'transaction_id', 'payment_status', 'payment_date', 'invoice_number']

class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = '__all__'

class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = '__all__'

class BranchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = '__all__'
