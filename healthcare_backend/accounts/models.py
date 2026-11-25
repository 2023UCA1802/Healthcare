from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("An email address is required.")
        email = self.normalize_email(email).strip().lower()
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self._create_user(email, password, **extra)


class User(AbstractUser):
    """Email is the login identifier (no separate username)."""

    username = None
    first_name = None
    last_name = None
    name = models.CharField(max_length=150)
    email = models.EmailField(unique=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="unique_user_email_ci"),
        ]

    def save(self, *args, **kwargs):
        self.email = (self.email or "").strip().lower()
        super().save(*args, **kwargs)

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return self.name


class RevokedSession(models.Model):
    """Sessions (one per login) that were logged out.

    Every token issued at login carries a random session id (`sid`). Access tokens
    are otherwise stateless, so this small denylist is how logout kills them
    immediately instead of waiting for them to expire.
    """

    sid = models.CharField(max_length=32, unique=True)  # unique -> indexed lookup
    revoked_at = models.DateTimeField(auto_now_add=True)
    # After this moment no token of the session can still be valid, so the row
    # can be purged (python manage.py flushrevokedsessions).
    expires_at = models.DateTimeField(db_index=True)

    def __str__(self):
        return f"revoked session {self.sid[:8]}..."