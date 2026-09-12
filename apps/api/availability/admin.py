from django.contrib import admin

from availability.models import AvailabilityBlock, ExternalCalendar


@admin.register(AvailabilityBlock)
class AvailabilityBlockAdmin(admin.ModelAdmin):
    list_display = ("property", "kind", "start", "end", "booking", "external_calendar")
    list_filter = ("kind",)
    search_fields = ("property__title",)
    readonly_fields = ("booking", "external_calendar", "external_uid")


@admin.register(ExternalCalendar)
class ExternalCalendarAdmin(admin.ModelAdmin):
    list_display = ("property", "source", "last_synced_at", "last_error")
    list_filter = ("source",)
    readonly_fields = ("last_synced_at", "last_error")
