from django.db import models
from django.conf import settings
from schools.models import School
from academics.models import Section, Subject

class TimetableConfig(models.Model):
    school = models.OneToOneField(School, on_delete=models.CASCADE, related_name='timetable_config')
    start_time = models.TimeField(help_text="School opening time")
    end_time = models.TimeField(help_text="School closing time")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Config for {self.school.name}"

class DailyActivity(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='daily_activities')
    name = models.CharField(max_length=100)  # e.g., Prayer, Lunch Break
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_break = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Daily Activities"
        ordering = ['start_time']

    def __str__(self):
        return f"{self.name} ({self.start_time} - {self.end_time})"

class PeriodSlot(models.Model):
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='period_slots')
    period_number = models.PositiveIntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        unique_together = ('school', 'period_number')
        ordering = ['period_number']

    def __str__(self):
        return f"Period {self.period_number}: {self.start_time} - {self.end_time}"

class TimetableEntry(models.Model):
    DAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='timetable_entries')
    section = models.ForeignKey(Section, on_delete=models.CASCADE, related_name='timetable_entries')
    day = models.CharField(max_length=10, choices=DAY_CHOICES)
    slot = models.ForeignKey(PeriodSlot, on_delete=models.CASCADE, related_name='entries')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name='timetable_entries')
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name='timetable_assignments'
    )

    class Meta:
        unique_together = [
            ('section', 'day', 'slot'),  # A class cannot have multiple subjects in the same period
        ]
        verbose_name_plural = "Timetable Entries"

    def __str__(self):
        return f"{self.section} - {self.day} - {self.slot} - {self.subject}"
