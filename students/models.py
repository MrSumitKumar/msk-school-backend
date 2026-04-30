from django.db import models
from accounts.soft_delete import SoftDeleteMixin


class StudentProfile(SoftDeleteMixin, models.Model):
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='student_profile')
    admission_number = models.CharField(max_length=50, unique=True, editable=False, null=True, blank=True)
    grade = models.ForeignKey('academics.Grade', on_delete=models.SET_NULL, null=True, related_name='students')
    section = models.ForeignKey('academics.Section', on_delete=models.SET_NULL, null=True, related_name='students')
    roll_number = models.PositiveIntegerField(editable=False, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('male','Male'),('female','Female'),('other','Other')], blank=True)
    blood_group = models.CharField(max_length=5, blank=True)
    address = models.TextField(blank=True)
    # Parent Info
    parent_name = models.CharField(max_length=200, blank=True)
    parent_contact = models.CharField(max_length=20, blank=True)
    parent_email = models.EmailField(blank=True)
    parent_occupation = models.CharField(max_length=100, blank=True)
    # Academic
    admission_date = models.DateField(null=True, blank=True)
    academic_session = models.ForeignKey(
        'academics.AcademicSession', on_delete=models.SET_NULL, null=True, blank=True
    )
    is_active = models.BooleanField(default=True)

    def save(self, *args, **kwargs):
        # Detect if section has changed to reset roll number
        if self.pk:
            old_instance = StudentProfile.objects.filter(pk=self.pk).first()
            if old_instance and old_instance.section_id != self.section_id:
                self.roll_number = None

        # Auto-generate Admission Number (Global uniqueness)
        if not self.admission_number:
            last_student = StudentProfile.objects.everything().filter(
                admission_number__startswith='ADM'
            ).order_by('-id').first()

            if last_student and last_student.admission_number:
                try:
                    num = int(last_student.admission_number[3:]) + 1
                    self.admission_number = f"ADM{num:04d}" if num < 1000 else f"ADM{num}"
                except (ValueError, IndexError):
                    self.admission_number = "ADM1001"
            else:
                self.admission_number = "ADM1001"

        # Auto-generate Roll Number (Section-scoped)
        if not self.roll_number and self.section:
            last_roll = StudentProfile.objects.everything().filter(section=self.section).order_by('-roll_number').first()
            self.roll_number = (last_roll.roll_number + 1) if (last_roll and last_roll.roll_number) else 1
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.full_name} ({self.admission_number})"
