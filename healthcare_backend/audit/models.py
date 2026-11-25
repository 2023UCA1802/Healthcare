from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Append-only record of who did what to which record (who viewed a patient, etc.)."""

    class Action(models.TextChoices):
        LOGIN_SUCCESS = "LOGIN_SUCCESS"
        LOGIN_FAILED = "LOGIN_FAILED"
        LOGOUT = "LOGOUT"
        REGISTER = "REGISTER"
        LIST = "LIST"
        VIEW = "VIEW"
        CREATE = "CREATE"
        UPDATE = "UPDATE"
        DELETE = "DELETE"

    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="audit_logs",
    )
    user_email = models.CharField(max_length=254, blank=True)  # kept even if the user row goes
    action = models.CharField(max_length=20, choices=Action.choices)
    resource_type = models.CharField(max_length=40, blank=True)
    resource_id = models.PositiveBigIntegerField(null=True, blank=True)
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-timestamp", "-id"]
        indexes = [
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["resource_type", "resource_id"]),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValueError("Audit log entries are append-only.")
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.timestamp:%Y-%m-%d %H:%M:%S} {self.user_email or '-'} {self.action} {self.resource_type}#{self.resource_id}"
