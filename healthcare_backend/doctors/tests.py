from core.testing import BaseAPITestCase
from doctors.models import Doctor
from mappings.models import PatientDoctorMapping
from patients.models import Patient

DOC = {"name": "Meera Shah", "email": "meera@hospital.com", "specialization": "Cardiology", "experience_years": 10}


class DoctorTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.alice = self.make_user("alice@example.com", "Alice")
        self.bob = self.make_user("bob@example.com", "Bob")
        self.a = self.client_for(self.alice)
        self.b = self.client_for(self.bob)

    def test_doctors_are_private_to_their_creator(self):
        d = self.a.post("/api/doctors/", DOC, format="json").json()
        self.assertEqual(self.b.get("/api/doctors/").json()["count"], 0)
        self.assertEqual(self.b.get(f"/api/doctors/{d['id']}/").status_code, 404)
        self.assertEqual(self.b.delete(f"/api/doctors/{d['id']}/").status_code, 404)

    def test_same_email_allowed_for_different_users_but_not_twice_for_one(self):
        self.assertEqual(self.a.post("/api/doctors/", DOC, format="json").status_code, 201)
        self.assertEqual(self.b.post("/api/doctors/", DOC, format="json").status_code, 201)  # no cross-user leak
        dup = self.a.post("/api/doctors/", {**DOC, "email": "MEERA@hospital.com"}, format="json")
        self.assertEqual(dup.status_code, 400)

    def test_update_own_doctor_keeping_same_email(self):
        d = self.a.post("/api/doctors/", DOC, format="json").json()
        res = self.a.put(f"/api/doctors/{d['id']}/", {**DOC, "experience_years": 11}, format="json")
        self.assertEqual(res.status_code, 200)

    def test_cannot_delete_doctor_assigned_to_live_patient(self):
        d = Doctor.objects.create(created_by=self.alice, **DOC)
        p = Patient.objects.create(created_by=self.alice, name="P", age=1, gender="M")
        PatientDoctorMapping.objects.create(patient=p, doctor=d)
        res = self.a.delete(f"/api/doctors/{d.id}/")
        self.assertEqual(res.status_code, 409)
        self.assertTrue(Doctor.objects.filter(pk=d.pk).exists())

    def test_assignment_to_soft_deleted_patient_does_not_block_delete(self):
        d = Doctor.objects.create(created_by=self.alice, **DOC)
        p = Patient.objects.create(created_by=self.alice, name="P", age=1, gender="M")
        PatientDoctorMapping.objects.create(patient=p, doctor=d)
        p.soft_delete()
        self.assertEqual(self.a.delete(f"/api/doctors/{d.id}/").status_code, 204)
        self.assertFalse(Doctor.objects.filter(pk=d.pk).exists())
