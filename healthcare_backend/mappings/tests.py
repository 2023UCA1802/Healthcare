from core.testing import BaseAPITestCase
from doctors.models import Doctor
from mappings.models import PatientDoctorMapping
from patients.models import Patient


class MappingTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.alice = self.make_user("alice@example.com", "Alice")
        self.bob = self.make_user("bob@example.com", "Bob")
        self.a = self.client_for(self.alice)
        self.b = self.client_for(self.bob)
        self.patient = Patient.objects.create(created_by=self.alice, name="P", age=30, gender="M")
        self.doctor = Doctor.objects.create(created_by=self.alice, name="D", email="d@x.com", specialization="ENT")

    def assign(self, client=None, patient=None, doctor=None):
        return (client or self.a).post(
            "/api/mappings/",
            {"patient": (patient or self.patient).id, "doctor": (doctor or self.doctor).id}, format="json",
        )

    def test_assign_list_and_per_patient_view(self):
        self.assertEqual(self.assign().status_code, 201)
        self.assertEqual(self.a.get("/api/mappings/").json()["count"], 1)
        doctors = self.a.get(f"/api/mappings/{self.patient.id}/").json()
        self.assertEqual(doctors[0]["doctor"]["name"], "D")

    def test_duplicate_assignment_rejected(self):
        self.assign()
        self.assertEqual(self.assign().status_code, 400)

    def test_cannot_use_someone_elses_patient_or_doctor(self):
        bobs_doc = Doctor.objects.create(created_by=self.bob, name="BD", email="bd@x.com", specialization="X")
        self.assertEqual(self.assign(client=self.b).status_code, 400)  # alice's patient + alice's doctor
        self.assertEqual(self.assign(doctor=bobs_doc).status_code, 400)  # alice's patient + bob's doctor
        self.assertEqual(PatientDoctorMapping.objects.count(), 0)

    def test_other_users_cannot_read_or_delete_mappings(self):
        m = PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)
        self.assertEqual(self.b.get("/api/mappings/").json()["count"], 0)
        self.assertEqual(self.b.get(f"/api/mappings/{self.patient.id}/").status_code, 404)
        self.assertEqual(self.b.delete(f"/api/mappings/{m.id}/").status_code, 404)
        self.assertEqual(self.a.delete(f"/api/mappings/{m.id}/").status_code, 204)

    def test_soft_deleted_patient_disappears_from_mappings_and_cannot_be_assigned(self):
        PatientDoctorMapping.objects.create(patient=self.patient, doctor=self.doctor)
        self.patient.soft_delete()
        self.assertEqual(self.a.get("/api/mappings/").json()["count"], 0)
        self.assertEqual(self.a.get(f"/api/mappings/{self.patient.id}/").status_code, 404)
        self.assertEqual(self.assign().status_code, 400)
