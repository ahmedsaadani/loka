from django.contrib import admin

from bookings.models import Booking, BookingRequest, Payment


@admin.register(BookingRequest)
class BookingRequestAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "property",
        "traveler",
        "rental_mode",
        "start_date",
        "end_date",
        "status",
        "expires_at",
    )
    list_filter = ("status", "rental_mode")
    search_fields = ("public_id", "property__title", "traveler__email")
    readonly_fields = [f.name for f in BookingRequest._meta.fields]


class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = (
        "provider",
        "provider_ref",
        "amount",
        "currency",
        "kind",
        "status",
        "created_at",
    )
    can_delete = False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "property",
        "traveler",
        "host",
        "start_date",
        "end_date",
        "status",
        "total_amount",
    )
    list_filter = ("status", "rental_mode")
    search_fields = ("public_id", "property__title", "traveler__email", "host__email")
    readonly_fields = [f.name for f in Booking._meta.fields]
    inlines = [PaymentInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "booking",
        "kind",
        "amount",
        "currency",
        "provider",
        "status",
        "created_at",
    )
    list_filter = ("kind", "status", "provider")
    search_fields = ("provider_ref", "booking__public_id")
    readonly_fields = [f.name for f in Payment._meta.fields]
