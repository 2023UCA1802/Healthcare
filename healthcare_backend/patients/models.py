from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from core.fields import EncryptedTextField


class Patient(models.Model):
    class Gender(models.TextChoices):
        MALE = "M", "Male"
        FEMALE = "F", "Female"
        OTHER = "O", "Other"

    # PROTECT: a user who owns patient records can't be deleted by accident
    # (deactivate them instead).
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="patients"
    )
    name = models.CharField(max_length=150)
    age = models.PositiveSmallIntegerField(validators=[MinValueValidator(0), MaxValueValidator(150)])
    gender = models.CharField(max_length=1, choices=Gender.choices)
    # Encrypted at rest (see core/fields.py)
    phone = EncryptedTextField(blank=True, default="")
    address = EncryptedTextField(blank=True, default="")
    medical_history = EncryptedTextField(blank=True, default="")
    # Soft delete: records are hidden, never physically removed by the API.
    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def soft_delete(self):
        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at", "updated_at"])

    def __str__(self):
        return f"{self.name} ({self.pk})"
