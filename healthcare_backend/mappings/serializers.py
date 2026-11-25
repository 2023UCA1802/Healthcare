from rest_framework import serializers

from doctors.serializers import DoctorSerializer

from .models import PatientDoctorMapping


class MappingSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)
    doctor_name = serializers.CharField(source="doctor.name", read_only=True)

    class Meta:
        model = PatientDoctorMapping
        fields = ("id", "patient", "patient_name", "doctor", "doctor_name", "assigned_at")
        read_only_fields = ("id", "assigned_at")
        validators = []  # we run the duplicate check ourselves for a clearer message

    def validate_patient(self, patient):
        user = self.context["request"].user
        if patient.created_by_id != user.id or patient.is_deleted:
            raise serializers.ValidationError("Patient not found.")
        return patient

    def validate_doctor(self, doctor):
        if doctor.created_by_id != self.context["request"].user.id:
            raise serializers.ValidationError("Doctor not found.")
        return doctor

    def validate(self, attrs):
        if PatientDoctorMapping.objects.filter(
            patient=attrs["patient"], doctor=attrs["doctor"]
        ).exists():
            raise serializers.ValidationError("This doctor is already assigned to this patient.")
        return attrs


class PatientDoctorSerializer(serializers.ModelSerializer):
    """Used for GET /api/mappings/<patient_id>/ — returns the doctor details."""

    doctor = DoctorSerializer(read_only=True)

    class Meta:
        model = PatientDoctorMapping
        fields = ("id", "doctor", "assigned_at")
