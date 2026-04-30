from django.contrib import admin
from .models import School, SubscriptionPlan, Subscription, Payment, Invoice, Notification, Branch


@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'max_students', 'max_teachers', 'price', 'duration_months')
    ordering = ('price',)


@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'board_type', 'contact_email', 'subscription_plan', 'is_active', 'created_at')
    list_filter = ('board_type', 'is_active', 'subscription_plan')
    search_fields = ('name', 'contact_email')


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('school', 'plan', 'start_date', 'end_date', 'status', 'is_active', 'created_at')
    list_filter = ('status', 'is_active', 'plan')
    search_fields = ('school__name',)
    ordering = ('-created_at',)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('school', 'plan', 'amount', 'payment_method', 'transaction_id', 'payment_status', 'invoice_number', 'payment_date')
    list_filter = ('payment_status', 'payment_method', 'plan')
    search_fields = ('school__name', 'transaction_id', 'invoice_number')
    ordering = ('-payment_date',)
    readonly_fields = ('payment_date',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'school_name', 'plan_name', 'amount', 'status', 'payment_date', 'created_at')
    list_filter = ('status',)
    search_fields = ('invoice_number', 'school_name')
    ordering = ('-payment_date',)
    readonly_fields = ('payment_date', 'created_at')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('school', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('school__name', 'message')
    ordering = ('-created_at',)


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('school', 'name', 'branch_code', 'city', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('school__name', 'name', 'branch_code')
