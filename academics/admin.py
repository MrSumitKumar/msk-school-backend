from django.contrib import admin
from .models import AcademicSession, Grade, Section, Subject, GradeSubject, Book, Period

admin.site.register(AcademicSession)
admin.site.register(Grade)
admin.site.register(Section)
admin.site.register(Subject)
admin.site.register(GradeSubject)
admin.site.register(Book)
admin.site.register(Period)
