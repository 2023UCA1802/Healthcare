from django.db import transaction
from rest_framework import generics

from audit.mixins import AuditedMixin

from .models import Doctor
from .serializers import DoctorSerializer


class _OwnDoctorsMixin:
    def get_queryset(self):
        return Doctor.objects.filter(created_by=self.request.user)


class DoctorListCreateView(AuditedMixin, _OwnDoctorsMixin, generics.ListCreateAPIView):
    serializer_class = DoctorSerializer
    audit_resource = "doctor"

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class DoctorDetailView(AuditedMixin, _OwnDoctorsMixin, generics.RetrieveUpdateDestroyAPIView):
    serializer_class = DoctorSerializer
    audit_resource = "doctor"

    @transaction.atomic
    def perform_destroy(self, instance):
        # Assignments to soft-deleted patients are invisible to the user, so they
        # must not block deletion. Assignments to live patients still do (PROTECT -> 409).
        instance.mappings.filter(patient__is_deleted=True).delete()
        instance.delete()
