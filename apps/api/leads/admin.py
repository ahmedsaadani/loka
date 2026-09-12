from django.contrib import admin

from leads.models import Lead


@admin.register(Lead)
class LeadAdmin(admin.ModelAdmin):
    list_display = ("title", "source", "city", "price", "status", "assigned_to", "created_at")
    list_filter = ("source", "status", "city")
    search_fields = ("title", "phone", "source_url", "notes")
    readonly_fields = ("public_id", "status", "converted_property", "created_at", "updated_at")
