from django.db import models


class AcademicSession(models.Model):
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='sessions')
    name = models.CharField(max_length=50)  # e.g. 2025-2026
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)

    class Meta:
        unique_together = ('school', 'name')

    def __str__(self):
        return f"{self.school.name} - {self.name}"


class Grade(models.Model):
    LEVEL_CHOICES = [
        ('pre_primary', 'Pre-Primary'),
        ('primary', 'Primary'),
        ('middle', 'Middle'),
        ('secondary', 'Secondary'),
        ('senior_secondary', 'Senior Secondary'),
    ]
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='grades')
    name = models.CharField(max_length=50)   # Nursery, LKG, 1, 2 ... 12
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, blank=True)
    order = models.IntegerField(default=0)   # for sorting

    class Meta:
        unique_together = ('school', 'name')
        ordering = ['order', 'name']

    def __str__(self):
        return f"Grade {self.name} - {self.school.name}"


class Section(models.Model):
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='sections', null=True)
    name = models.CharField(max_length=10)   # A, B, C
    class_teacher = models.OneToOneField(
        'teachers.TeacherProfile', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='teaching_section'
    )

    class Meta:
        unique_together = ('grade', 'name')
        ordering = ['name']

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.upper()
        super().save(*args, **kwargs)

    def __str__(self):
        grade_name = self.grade.name if self.grade else "Unknown"
        return f"Grade {grade_name} - Section {self.name}"


class Subject(models.Model):
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='subjects')
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = ('school', 'name')

    def __str__(self):
        return f"{self.name} ({self.school.name})"


class GradeSubject(models.Model):
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='grade_subjects', null=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='grade_subjects')
    teacher = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='assigned_subjects'
    )

    class Meta:
        unique_together = ('grade', 'subject')

    def __str__(self):
        return f"{self.grade} - {self.subject}"


class Book(models.Model):
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE, related_name='books')
    grade = models.ForeignKey(Grade, on_delete=models.CASCADE, related_name='books', null=True)
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='books')
    title = models.CharField(max_length=200)
    author = models.CharField(max_length=200, blank=True)
    publisher = models.CharField(max_length=200, blank=True)
    isbn = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.title} - Grade {self.grade.name}"


class Period(models.Model):
    DAY_CHOICES = [
        ('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'), ('friday', 'Friday'), ('saturday', 'Saturday'),
    ]
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='periods')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='periods')
    teacher = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='periods'
    )
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    period_number = models.IntegerField()

    class Meta:
        unique_together = ('section', 'day', 'period_number')
        ordering = ['day', 'period_number']

    def __str__(self):
        return f"{self.section} | {self.day} | Period {self.period_number} - {self.subject.name}"
