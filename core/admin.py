from django.contrib import admin
from .models import HealthCheckLog


@admin.register(HealthCheckLog)
class HealthCheckLogAdmin(admin.ModelAdmin):
    """Admin interface for HealthCheckLog model."""
    list_display = ['timestamp', 'service', 'status', 'short_details']
    list_filter = ['service', 'status', 'timestamp']
    search_fields = ['details']
    readonly_fields = ['timestamp']
    ordering = ['-timestamp']
    date_hierarchy = 'timestamp'
    
    def short_details(self, obj):
        """Display truncated details in list view."""
        if len(obj.details) > 50:
            return f"{obj.details[:47]}..."
        return obj.details
    short_details.short_description = 'Details'
