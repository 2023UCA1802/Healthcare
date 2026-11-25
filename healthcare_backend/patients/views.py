from rest_framework import generics

from audit.mixins import AuditedMixin

from .models import Patient
from .serializers import PatientSerializer


class _OwnPatientsMixin:
    def get_queryset(self):
        # Only the caller's own, non-deleted patients: anyone else's -> 404.
        return Patient.objects.filter(created_by=self.request.user, is_deleted=False)


class PatientListCreateView(AuditedMixin, _OwnPatientsMixin, generics.ListCreateAPIView):
    serializer_class = PatientSerializer
    audit_resource = "patient"

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class PatientDetailView(AuditedMixin, _OwnPatientsMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PatientSerializer
    audit_resource = "patient"

    def perform_destroy(self, instance):
        instance.soft_delete()
