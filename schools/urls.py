from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'plans', views.SubscriptionPlanViewSet, basename='plan')
router.register(r'subscriptions', views.SubscriptionViewSet, basename='subscription')
router.register(r'payments', views.PaymentViewSet, basename='payment')
router.register(r'invoices', views.InvoiceViewSet, basename='invoice')
router.register(r'notifications', views.NotificationViewSet, basename='notification')
router.register(r'branches', views.BranchViewSet, basename='branch')

urlpatterns = [
    path('', views.SchoolListCreateView.as_view(), name='school-list'),
    path('<int:pk>/', views.SchoolDetailView.as_view(), name='school-detail'),
    path('settings/profile/', views.SchoolSettingsView.as_view(), name='school-settings'),
    path('saas-dashboard/', views.super_admin_dashboard_stats, name='saas-dashboard'),
    path('billing/current-plan/', views.get_current_subscription, name='current-subscription'),
    # ── Razorpay ──────────────────────────────────────
    path('billing/razorpay/create-order/', views.create_razorpay_order, name='razorpay-create-order'),
    path('billing/razorpay/verify-payment/', views.verify_razorpay_payment, name='razorpay-verify-payment'),
    path('billing/razorpay/webhook/', views.razorpay_webhook, name='razorpay-webhook'),
    # ── PhonePe ───────────────────────────────────────
    path('billing/phonepe/create-order/', views.create_phonepe_order, name='phonepe-create-order'),
    path('billing/phonepe/verify-payment/', views.verify_phonepe_payment, name='phonepe-verify-payment'),
    # ── Binance Pay ───────────────────────────────────
    path('billing/binance/create-order/', views.create_binance_order, name='binance-create-order'),
    path('billing/binance/verify-payment/', views.verify_binance_payment, name='binance-verify-payment'),
    path('', include(router.urls)),
]
