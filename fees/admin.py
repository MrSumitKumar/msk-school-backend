from django.contrib import admin
from .models import FeeCategory, FeeStructure, FeePayment, FeeInstallment

admin.site.register(FeeCategory)
admin.site.register(FeeStructure)
admin.site.register(FeeInstallment)
admin.site.register(FeePayment)
