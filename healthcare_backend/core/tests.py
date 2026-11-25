from cryptography.fernet import Fernet
from django.test import SimpleTestCase, override_settings

from core.fields import EncryptedTextField


class EncryptedFieldTests(SimpleTestCase):
    field = EncryptedTextField()

    def roundtrip(self, value):
        return self.field.from_db_value(self.field.get_prep_value(value), None, None)

    def test_roundtrip_unicode_empty_and_none(self):
        self.assertEqual(self.roundtrip("हृदय रोग / café"), "हृदय रोग / café")
        self.assertEqual(self.roundtrip(""), "")
        self.assertIsNone(self.roundtrip(None))

    def test_ciphertext_differs_from_plaintext_and_is_randomised(self):
        a, b = self.field.get_prep_value("secret"), self.field.get_prep_value("secret")
        self.assertNotIn("secret", a)
        self.assertNotEqual(a, b)

    def test_key_rotation_old_data_still_readable(self):
        old, new = Fernet.generate_key().decode(), Fernet.generate_key().decode()
        with override_settings(FIELD_ENCRYPTION_KEYS=[old]):
            stored = self.field.get_prep_value("history")
        with override_settings(FIELD_ENCRYPTION_KEYS=[new, old]):  # new key first
            self.assertEqual(self.field.from_db_value(stored, None, None), "history")
        with override_settings(FIELD_ENCRYPTION_KEYS=[new]):  # old key dropped -> loud failure
            with self.assertRaises(Exception):
                self.field.from_db_value(stored, None, None)
