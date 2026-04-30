from django.urls import path
from . import views

urlpatterns = [
    path('categories/', views.FeeCategoryListCreateView.as_view(), name='fee-category-list'),
    path('structures/', views.FeeStructureListCreateView.as_view(), name='fee-structure-list'),
    path('structures/<int:pk>/', views.FeeStructureDetailView.as_view(), name='fee-structure-detail'),
    path('installments/', views.FeeInstallmentListCreateView.as_view(), name='fee-installment-list'),
    path('installments/<int:pk>/', views.FeeInstallmentDetailView.as_view(), name='fee-installment-detail'),
    path('payments/', views.FeePaymentListCreateView.as_view(), name='fee-payment-list'),
    path('payments/<int:pk>/', views.FeePaymentDetailView.as_view(), name='fee-payment-detail'),
    path('payments/<int:payment_id>/receipt/', views.generate_fee_receipt, name='fee-receipt'),
]
