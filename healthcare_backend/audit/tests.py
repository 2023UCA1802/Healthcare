from audit.models import AuditLog
from core.testing import BaseAPITestCase
from patients.models import Patient


class AuditTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.alice = self.make_user("alice@example.com", "Alice")
        self.bob = self.make_user("bob@example.com", "Bob")
        self.a = self.client_for(self.alice)
        self.patient = Patient.objects.create(created_by=self.alice, name="P", age=30, gender="M")

    def last(self):
        return AuditLog.objects.first()

    def test_every_patient_operation_is_recorded(self):
        pid = self.patient.id
        self.a.get("/api/patients/")
        self.assertEqual((self.last().action, self.last().resource_type), ("LIST", "patient"))
        self.a.get(f"/api/patients/{pid}/")
        entry = self.last()
        self.assertEqual((entry.action, entry.resource_id, entry.user, entry.status_code), ("VIEW", pid, self.alice, 200))
        self.assertEqual(entry.user_email, "alice@example.com")
        self.assertIsNotNone(entry.ip_address)
        self.a.put(f"/api/patients/{pid}/", {"name": "P2", "age": 31, "gender": "M"}, format="json")
        self.assertEqual(self.last().action, "UPDATE")
        created = self.a.post("/api/patients/", {"name": "N", "age": 1, "gender": "F"}, format="json").json()
        self.assertEqual((self.last().action, self.last().resource_id), ("CREATE", created["id"]))
        self.a.delete(f"/api/patients/{pid}/")
        self.assertEqual(self.last().action, "DELETE")

    def test_snooping_on_someone_elses_patient_is_logged_with_404(self):
        self.client_for(self.bob).get(f"/api/patients/{self.patient.id}/")
        entry = self.last()
        self.assertEqual((entry.user, entry.action, entry.resource_id, entry.status_code), (self.bob, "VIEW", self.patient.id, 404))

    def test_audit_log_never_stores_patient_data(self):
        self.a.get(f"/api/patients/{self.patient.id}/")
        fields = {f.name for f in AuditLog._meta.fields}
        self.assertTrue(fields.isdisjoint({"medical_history", "address", "phone", "name"}))

    def test_entries_are_append_only(self):
        self.a.get("/api/patients/")
        entry = self.last()
        entry.action = "DELETE"
        with self.assertRaises(ValueError):
            entry.save()
