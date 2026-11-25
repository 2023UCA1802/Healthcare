from django.conf import settings
from django.core.validators import MaxValueValidator
from django.db import models


class Doctor(models.Model):
    """A doctor in one user's own directory (doctors are private to their creator)."""

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="doctors"
    )
    name = models.CharField(max_length=150)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    specialization = models.CharField(max_length=100)
    experience_years = models.PositiveSmallIntegerField(
        default=0, validators=[MaxValueValidator(80)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name", "id"]
        constraints = [
            models.UniqueConstraint(fields=["created_by", "email"], name="unique_doctor_email_per_user")
        ]

    def __str__(self):
        return f"Dr. {self.name} ({self.specialization})"
