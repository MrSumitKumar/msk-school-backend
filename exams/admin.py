from django.contrib import admin
from .models import Exam, ExamSchedule, ExamResult
admin.site.register(Exam)
admin.site.register(ExamSchedule)
admin.site.register(ExamResult)
