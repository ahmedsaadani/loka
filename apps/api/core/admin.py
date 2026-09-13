from typing import Any

from django.contrib import admin
from django.http import HttpRequest

from core.models import SensitiveAccessLog, SiteContent, StatusLog


@admin.register(StatusLog)
class StatusLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "content_type", "object_id", "from_status", "to_status", "actor")
    list_filter = ("content_type", "to_status")
    readonly_fields = ("created_at", "updated_at")
    search_fields = ("object_id", "note")


@admin.register(SensitiveAccessLog)
class SensitiveAccessLogAdmin(admin.ModelAdmin):
    list_display = ("accessed_at", "kind", "target_type", "target_id", "actor", "ip_address")
    list_filter = ("kind",)
    readonly_fields = [f.name for f in SensitiveAccessLog._meta.fields]

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: Any = None) -> bool:
        return False


@admin.register(SiteContent)
class SiteContentAdmin(admin.ModelAdmin):
    list_display = ("key", "title", "is_published", "updated_at", "needs_writing")
    search_fields = ("key", "title", "body")
    readonly_fields = ("created_at", "updated_at")

    @admin.display(boolean=True, description="À rédiger")
    def needs_writing(self, obj: SiteContent) -> bool:
        return "[À RÉDIGER]" in obj.title or "[À RÉDIGER]" in obj.body
