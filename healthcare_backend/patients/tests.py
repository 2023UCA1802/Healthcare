from django.db import connection

from core.testing import BaseAPITestCase
from patients.models import Patient

PAYLOAD = {
    "name": "Ravi Kumar", "age": 42, "gender": "M", "phone": "9999999999",
    "address": "12 MG Road, Pune", "medical_history": "Type 2 diabetes",
}


class PatientTests(BaseAPITestCase):
    def setUp(self):
        super().setUp()
        self.alice = self.make_user("alice@example.com", "Alice")
        self.bob = self.make_user("bob@example.com", "Bob")
        self.a = self.client_for(self.alice)
        self.b = self.client_for(self.bob)

    def create(self, client=None):
        res = (client or self.a).post("/api/patients/", PAYLOAD, format="json")
        self.assertEqual(res.status_code, 201, res.content)
        return res.json()

    def test_create_sets_owner_and_ignores_client_supplied_owner(self):
        res = self.a.post("/api/patients/", {**PAYLOAD, "created_by": self.bob.id}, format="json")
        self.assertEqual(Patient.objects.get(pk=res.json()["id"]).created_by, self.alice)
        self.assertNotIn("created_by", res.json())

    def test_other_users_patients_are_invisible(self):
        p = self.create()
        self.assertEqual(self.b.get("/api/patients/").json()["count"], 0)
        for method in ("get", "put", "delete"):
            kwargs = {"data": PAYLOAD, "format": "json"} if method == "put" else {}
            res = getattr(self.b, method)(f"/api/patients/{p['id']}/", **kwargs)
            self.assertEqual(res.status_code, 404, method)
        self.assertEqual(self.a.get(f"/api/patients/{p['id']}/").status_code, 200)

    def test_sensitive_fields_are_encrypted_in_the_database_but_plain_in_the_api(self):
        p = self.create()
        with connection.cursor() as cur:
            cur.execute("SELECT phone, address, medical_history FROM patients_patient WHERE id=%s", [p["id"]])
            raw = cur.fetchone()
        for stored, plain in zip(raw, (PAYLOAD["phone"], PAYLOAD["address"], PAYLOAD["medical_history"])):
            self.assertNotIn(plain, stored)
            self.assertTrue(stored.startswith("gAAAA"))  # Fernet token
        body = self.a.get(f"/api/patients/{p['id']}/").json()
        self.assertEqual(body["medical_history"], "Type 2 diabetes")
        self.assertEqual(body["phone"], "9999999999")

    def test_empty_optional_fields_round_trip(self):
        res = self.a.post("/api/patients/", {"name": "X", "age": 1, "gender": "F"}, format="json")
        self.assertEqual(res.status_code, 201)
        self.assertEqual(res.json()["phone"], "")

    def test_delete_is_soft(self):
        p = self.create()
        self.assertEqual(self.a.delete(f"/api/patients/{p['id']}/").status_code, 204)
        row = Patient.objects.get(pk=p["id"])  # still in the DB
        self.assertTrue(row.is_deleted)
        self.assertIsNotNone(row.deleted_at)
        self.assertEqual(self.a.get(f"/api/patients/{p['id']}/").status_code, 404)
        self.assertEqual(self.a.get("/api/patients/").json()["count"], 0)

    def test_validation(self):
        bad = self.a.post("/api/patients/", {**PAYLOAD, "phone": "1" * 21}, format="json")
        self.assertEqual(bad.status_code, 400)
        self.assertEqual(self.a.post("/api/patients/", {**PAYLOAD, "age": 200}, format="json").status_code, 400)
        self.assertEqual(self.a.post("/api/patients/", {**PAYLOAD, "name": "   "}, format="json").status_code, 400)

    def test_list_is_paginated_and_page_size_is_capped(self):
        for i in range(25):
            Patient.objects.create(created_by=self.alice, name=f"P{i}", age=1, gender="M")
        page1 = self.a.get("/api/patients/").json()
        self.assertEqual((page1["count"], len(page1["results"])), (25, 20))
        self.assertIsNotNone(page1["next"])
        self.assertEqual(len(self.a.get("/api/patients/?page=2").json()["results"]), 5)
        self.assertEqual(len(self.a.get("/api/patients/?page_size=1000").json()["results"]), 25)  # capped at 100

    def test_requires_authentication(self):
        from rest_framework.test import APIClient
        self.assertEqual(APIClient().get("/api/patients/").status_code, 401)
