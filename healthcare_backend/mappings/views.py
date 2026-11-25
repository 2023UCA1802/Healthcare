from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from audit.mixins import AuditedMixin
from patients.models import Patient

from .models import PatientDoctorMapping
from .serializers import MappingSerializer, PatientDoctorSerializer


class MappingListCreateView(AuditedMixin, generics.ListCreateAPIView):
    serializer_class = MappingSerializer
    audit_resource = "mapping"

    def get_queryset(self):
        # Only mappings of the caller's own, non-deleted patients.
        return PatientDoctorMapping.objects.filter(
            patient__created_by=self.request.user, patient__is_deleted=False
        ).select_related("patient", "doctor")


class MappingDetailView(AuditedMixin, APIView):
    """
    GET    /api/mappings/<patient_id>/ -> doctors assigned to that patient
    DELETE /api/mappings/<id>/         -> remove a mapping
    (Same URL shape, so the path parameter is interpreted per HTTP method.)
    """

    def get_audit_target(self, request, response):
        # GET reads a patient's doctor list; DELETE removes one mapping row.
        if request.method == "GET":
            return "patient_doctors", self.kwargs["pk"]
        return "mapping", self.kwargs["pk"]

    def get(self, request, pk):
        patient = get_object_or_404(Patient, pk=pk, created_by=request.user, is_deleted=False)
        mappings = patient.mappings.select_related("doctor")
        return Response(PatientDoctorSerializer(mappings, many=True).data)

    def delete(self, request, pk):
        mapping = get_object_or_404(
            PatientDoctorMapping, pk=pk, patient__created_by=request.user, patient__is_deleted=False
        )
        mapping.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
