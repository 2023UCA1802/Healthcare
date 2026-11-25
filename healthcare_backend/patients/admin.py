from django.contrib import admin

from .models import Patient


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "age", "gender", "created_by", "is_deleted", "created_at")
    list_filter = ("is_deleted", "gender")
    readonly_fields = ("created_at", "updated_at", "deleted_at")
