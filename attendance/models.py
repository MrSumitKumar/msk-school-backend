from django.db import models


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
        ('half_day', 'Half Day'),
        ('holiday', 'Holiday'),
    ]

    student = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='attendances')
    section = models.ForeignKey('academics.Section', on_delete=models.CASCADE, related_name='attendances')
    academic_session = models.ForeignKey(
        'academics.AcademicSession', on_delete=models.CASCADE, related_name='attendances'
    )
    date = models.DateField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='present')
    marked_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, related_name='marked_attendances'
    )
    remarks = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('student', 'date')
        ordering = ['-date']

    def __str__(self):
        return f"{self.student.full_name} - {self.date} - {self.status}"
