from django.db import models
import uuid
import json

class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Create'),
        ('UPDATE', 'Update'),
        ('SOFT_DELETE', 'Soft Delete'),
        ('RESTORE', 'Restore'),
        ('PERMANENT_DELETE', 'Permanent Delete'),
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    school = models.ForeignKey('schools.School', on_delete=models.SET_NULL, null=True, blank=True, related_name='audit_logs')
    action_type = models.CharField(max_length=20, choices=ACTION_CHOICES, db_index=True)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    object_repr = models.CharField(max_length=200)
    description = models.TextField()
    ip_address = models.CharField(max_length=45, blank=True)
    user_agent = models.TextField(blank=True)
    metadata = models.TextField(default='{}', blank=True, help_text="JSON formatted metadata")

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['timestamp', 'school', 'action_type']),
        ]

    def __str__(self):
        return f"{self.action_type} - {self.model_name} - {self.timestamp}"
