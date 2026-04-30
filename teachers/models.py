from django.db import models
from accounts.soft_delete import SoftDeleteMixin


class TeacherProfile(SoftDeleteMixin, models.Model):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='teacher_profile')
    employee_id = models.CharField(max_length=50, blank=True)
    qualification = models.CharField(max_length=200, blank=True)
    experience_years = models.IntegerField(default=0)
    joining_date = models.DateField(null=True, blank=True)
    designation = models.CharField(max_length=100, blank=True)  # e.g. HOD, Senior Teacher
    department = models.CharField(max_length=100, blank=True)
    salary = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    address = models.TextField(blank=True)
    emergency_contact = models.CharField(max_length=20, blank=True)
    def save(self, *args, **kwargs):
        if not self.employee_id:
            # Generate EMP ID (Global uniqueness)
            last_teacher = TeacherProfile.objects.everything().filter(
                employee_id__startswith='EMP'
            ).order_by('-id').first()

            if last_teacher and last_teacher.employee_id:
                try:
                    num = int(last_teacher.employee_id[3:]) + 1
                    self.employee_id = f"EMP{num:04d}" if num < 1000 else f"EMP{num}"
                except (ValueError, IndexError):
                    self.employee_id = "EMP1001"
            else:
                self.employee_id = "EMP1001"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.full_name} - {self.designation}"
