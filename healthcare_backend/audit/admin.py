from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("timestamp", "user_email", "action", "resource_type", "resource_id", "status_code", "ip_address")
    list_filter = ("action", "resource_type", "status_code")
    search_fields = ("user_email", "ip_address")
    date_hierarchy = "timestamp"

    # read-only in the admin
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
