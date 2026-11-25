from rest_framework import serializers

from .models import Patient


class PatientSerializer(serializers.ModelSerializer):
    # Encrypted columns are TextFields, so enforce the length limits here.
    phone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    address = serializers.CharField(max_length=500, required=False, allow_blank=True)
    medical_history = serializers.CharField(max_length=10000, required=False, allow_blank=True)

    class Meta:
        model = Patient
        fields = (
            "id", "name", "age", "gender", "phone", "address",
            "medical_history", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Name cannot be blank.")
        return value
