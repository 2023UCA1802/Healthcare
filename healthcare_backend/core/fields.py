"""Field-level encryption (Fernet: AES-128-CBC + HMAC-SHA256).

Values are encrypted before they hit the database and decrypted when loaded,
so a leaked DB dump or backup does not expose patient data.

Limits: encrypted columns cannot be searched/filtered/ordered in SQL.
Key rotation: put the NEW key first in FIELD_ENCRYPTION_KEYS and keep the old
ones after it; rows are re-encrypted with the new key the next time they save.
"""
from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models


def _fernet():
    return MultiFernet([Fernet(k.encode()) for k in settings.FIELD_ENCRYPTION_KEYS])


class EncryptedTextField(models.TextField):
    description = "Text encrypted at rest"

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        if value is None or value == "":
            return value
        return _fernet().encrypt(value.encode("utf-8")).decode("ascii")

    def from_db_value(self, value, expression, connection):
        if value is None or value == "":
            return value
        try:
            return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
        except InvalidToken as exc:
            raise ImproperlyConfigured(
                "Could not decrypt a stored value: wrong FIELD_ENCRYPTION_KEYS, "
                "or the row was stored unencrypted."
            ) from exc
