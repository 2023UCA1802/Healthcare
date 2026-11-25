from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import RevokedSession


class Command(BaseCommand):
    help = "Delete revoked-session rows that can no longer matter (all their tokens have expired)."

    def handle(self, *args, **options):
        deleted, _ = RevokedSession.objects.filter(expires_at__lt=timezone.now()).delete()
        self.stdout.write(f"Removed {deleted} expired revoked session(s).")