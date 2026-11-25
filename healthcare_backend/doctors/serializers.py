from rest_framework import serializers

from .models import Doctor


class DoctorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Doctor
        fields = (
            "id", "name", "email", "phone", "specialization",
            "experience_years", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
        validators = []  # per-user uniqueness is checked below with a friendlier message

    def validate_email(self, value):
        value = value.lower().strip()
        qs = Doctor.objects.filter(created_by=self.context["request"].user, email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("You already have a doctor with this email.")
        return value
