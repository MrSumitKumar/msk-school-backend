from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from .models import FeeCategory, FeeStructure, FeePayment, FeeInstallment


class FeeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = FeeCategory
        fields = '__all__'
        read_only_fields = ['school']


class FeeStructureSerializer(serializers.ModelSerializer):
    grade_name = serializers.ReadOnlyField(source='grade.name')
    category_name = serializers.ReadOnlyField(source='category.name')
    academic_session_name = serializers.ReadOnlyField(source='academic_session.name')
    effective_amount = serializers.SerializerMethodField()
    installment_amount = serializers.SerializerMethodField()

    class Meta:
        model = FeeStructure
        fields = '__all__'
        read_only_fields = ['school']

    def get_effective_amount(self, obj):
        return format(obj.effective_amount, '.2f')

    def get_installment_amount(self, obj):
        return format(obj.installment_amount, '.2f')

    def validate(self, attrs):
        request = self.context.get('request')
        school = getattr(request.user, 'school', None)
        installments = attrs.get('installments', getattr(self.instance, 'installments', 1))
        discount_percent = attrs.get('discount_percent', getattr(self.instance, 'discount_percent', 0))
        penalty_percent = attrs.get('late_fee_penalty_percent', getattr(self.instance, 'late_fee_penalty_percent', 0))
        frequency = attrs.get('frequency', getattr(self.instance, 'frequency', 'monthly'))

        if installments < 1:
            raise ValidationError({'installments': 'Installment count must be at least 1.'})
        if frequency == 'one_time' and installments > 1:
            raise ValidationError({'installments': 'One-time fees cannot be split into installments.'})
        if not 0 <= discount_percent <= 100:
            raise ValidationError({'discount_percent': 'Discount percent must be between 0 and 100.'})
        if not 0 <= penalty_percent <= 100:
            raise ValidationError({'late_fee_penalty_percent': 'Penalty percent must be between 0 and 100.'})

        if school:
            if installments > 1 and not school.has_feature('allow_installments'):
                raise ValidationError({'installments': 'Installment plans are not available for your subscription plan.'})
            if discount_percent > 0 and not school.has_feature('allow_discounts'):
                raise ValidationError({'discount_percent': 'Fee discounts are not available for your subscription plan.'})
            if penalty_percent > 0 and not school.has_feature('allow_penalties'):
                raise ValidationError({'late_fee_penalty_percent': 'Late payment penalties are not available for your subscription plan.'})

        return attrs


class FeeInstallmentSerializer(serializers.ModelSerializer):
    student_name = serializers.ReadOnlyField(source='student.full_name')
    fee_structure_name = serializers.ReadOnlyField(source='fee_structure.category.name')
    total_due = serializers.ReadOnlyField()
    balance_due = serializers.ReadOnlyField()

    class Meta:
        model = FeeInstallment
        fields = '__all__'

    def validate(self, attrs):
        if attrs.get('amount_due', 0) <= 0:
            raise ValidationError({'amount_due': 'Amount due must be greater than zero.'})
        if attrs.get('installment_number', 1) < 1:
            raise ValidationError({'installment_number': 'Installment number must be at least 1.'})
        fee_structure = attrs.get('fee_structure')
        if fee_structure and attrs.get('installment_number', 1) > fee_structure.installments:
            raise ValidationError({
                'installment_number': 'Installment number cannot exceed the defined installment count for the fee structure.'
            })
        return attrs


class FeePaymentSerializer(serializers.ModelSerializer):
    student_name = serializers.ReadOnlyField(source='student.full_name')
    collected_by_name = serializers.ReadOnlyField(source='collected_by.full_name')
    fee_structure_name = serializers.ReadOnlyField(source='fee_structure.category.name')
    installment_number = serializers.ReadOnlyField(source='installment.installment_number')
    balance_due = serializers.SerializerMethodField()
    total_due = serializers.SerializerMethodField()
    due_date = serializers.DateField(required=False, allow_null=True)

    class Meta:
        model = FeePayment
        fields = '__all__'

    def get_balance_due(self, obj):
        return float(obj.balance_due)

    def get_total_due(self, obj):
        return float(obj.total_due)

    def validate(self, attrs):
        amount_paid = attrs.get('amount_paid')
        if amount_paid is None or amount_paid <= 0:
            raise ValidationError({'amount_paid': 'Payment amount must be greater than zero.'})

        discount_amount = attrs.get('discount_amount', 0)
        scholarship_amount = attrs.get('scholarship_amount', 0)
        late_fee_amount = attrs.get('late_fee_amount', 0)

        if discount_amount < 0:
            raise ValidationError({'discount_amount': 'Discount amount cannot be negative.'})
        if scholarship_amount < 0:
            raise ValidationError({'scholarship_amount': 'Scholarship amount cannot be negative.'})
        if late_fee_amount < 0:
            raise ValidationError({'late_fee_amount': 'Late fee amount cannot be negative.'})

        installment = attrs.get('installment')
        fee_structure = attrs.get('fee_structure')
        amount_due = attrs.get('amount_due')

        if installment:
            expected_due = installment.total_due
            if amount_due is not None and amount_due != expected_due:
                raise ValidationError({'amount_due': 'Amount due must match the installment total due amount.'})
            attrs['amount_due'] = expected_due
            if attrs.get('due_date') is None:
                attrs['due_date'] = installment.due_date

        if amount_due is None and fee_structure is not None:
            if fee_structure.installments > 1:
                attrs['amount_due'] = fee_structure.installment_amount
            else:
                attrs['amount_due'] = fee_structure.effective_amount

        if attrs.get('amount_due') is None:
            raise ValidationError({'amount_due': 'Amount due is required when no installment is provided.'})

        if not attrs.get('due_date'):
            if installment:
                attrs['due_date'] = installment.due_date
            else:
                from datetime import date
                attrs['due_date'] = date.today()

        total_due = attrs['amount_due'] + attrs.get('late_fee_amount', 0) - attrs.get('discount_amount', 0) - attrs.get('scholarship_amount', 0)
        if total_due < 0:
            raise ValidationError({'amount_due': 'Total payable amount cannot be negative after adjustments.'})

        if amount_paid > total_due:
            raise ValidationError({'amount_paid': 'Payment cannot exceed the total due amount.'})

        transaction_id = attrs.get('transaction_id')
        if transaction_id:
            duplicate = FeePayment.objects.filter(
                student=attrs.get('student'),
                transaction_id=transaction_id
            )
            if self.instance:
                duplicate = duplicate.exclude(pk=self.instance.pk)
            if duplicate.exists():
                raise ValidationError({'transaction_id': 'This transaction ID has already been submitted for the student.'})

        payment_date = attrs.get('payment_date')
        due_date = attrs.get('due_date')
        if payment_date and due_date and payment_date < due_date and attrs.get('status') == 'overdue':
            raise ValidationError({'status': 'A payment cannot be marked overdue before the due date.'})

        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        if request and request.user and not validated_data.get('collected_by'):
            validated_data['collected_by'] = request.user
        payment = super().create(validated_data)
        payment.status = payment.compute_status()
        payment.save(update_fields=['status'])
        return payment
