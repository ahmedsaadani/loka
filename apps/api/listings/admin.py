from typing import Any

from django.contrib.gis import admin as gis_admin
from django.db.models import QuerySet
from django.http import HttpRequest

from listings.models import Amenity, PricingPlan, Property, PropertyAmenity, PropertyPhoto


class PropertyPhotoInline(gis_admin.TabularInline):
    model = PropertyPhoto
    extra = 0
    fields = ("order", "is_cover", "alt_text", "taken_by_team", "auto_enhance", "is_ready")
    readonly_fields = ("is_ready",)


class PricingPlanInline(gis_admin.TabularInline):
    model = PricingPlan
    extra = 0


class PropertyAmenityInline(gis_admin.TabularInline):
    model = PropertyAmenity
    extra = 0


@gis_admin.register(Property)
class PropertyAdmin(gis_admin.GISModelAdmin):
    list_display = (
        "title",
        "city",
        "neighborhood",
        "property_type",
        "status",
        "host",
        "published_at",
    )
    list_filter = ("status", "property_type", "city", "verification_level", "condition_grade")
    search_fields = ("title", "slug", "host__email")
    # Statut modifié uniquement via listings.services (ADR 0003).
    readonly_fields = (
        "public_id",
        "slug",
        "status",
        "verified_at",
        "verified_by",
        "published_at",
        "created_at",
        "updated_at",
    )
    inlines = [PropertyPhotoInline, PricingPlanInline, PropertyAmenityInline]
    actions = ["regenerate_variants"]

    def save_formset(self, request: HttpRequest, form: Any, formset: Any, change: bool) -> None:
        """Un changement de « retouche automatique » régénère les variantes de la photo."""
        super().save_formset(request, form, formset, change)
        if formset.model is not PropertyPhoto:
            return
        from core.tasks import enqueue
        from notifications.tasks import generate_photo_variants

        for photo_form in formset.forms:
            if "auto_enhance" in photo_form.changed_data and photo_form.instance.pk:
                enqueue(generate_photo_variants, photo_form.instance.pk)

    @gis_admin.action(description="Régénérer les variantes WebP des photos")
    def regenerate_variants(self, request: HttpRequest, queryset: QuerySet[Property]) -> None:
        from core.tasks import enqueue
        from notifications.tasks import generate_photo_variants

        count = 0
        for photo_id in PropertyPhoto.objects.filter(property__in=queryset).values_list(
            "pk", flat=True
        ):
            enqueue(generate_photo_variants, photo_id)
            count += 1
        self.message_user(request, f"{count} photo(s) en cours de régénération.")

    fieldsets = (
        (None, {"fields": ("host", "title", "slug", "public_id", "status", "description")}),
        (
            "Caractéristiques",
            {
                "fields": (
                    "property_type",
                    "rooms_label",
                    "bedrooms",
                    "bathrooms",
                    "surface_m2",
                    "floor",
                    "has_elevator",
                    "furnished",
                    "max_guests",
                    "condition_grade",
                )
            },
        ),
        (
            "Localisation (adresse exacte : interne)",
            {
                "fields": (
                    "city",
                    "neighborhood",
                    "address_private",
                    "location",
                    "location_precision",
                )
            },
        ),
        (
            "Vérification (interne)",
            {
                "fields": (
                    "verification_level",
                    "verified_at",
                    "verified_by",
                    "verification_notes",
                    "rejection_reason",
                    "visit_scheduled_at",
                )
            },
        ),
        (
            "Infos pratiques",
            {
                "fields": (
                    "charges_included",
                    "monthly_charges_estimate",
                    "deposit_months",
                    "min_lease_months",
                    "distance_notes",
                    "house_rules",
                )
            },
        ),
        ("SEO", {"fields": ("meta_title", "meta_description")}),
        ("Dates", {"fields": ("published_at", "created_at", "updated_at")}),
    )


@gis_admin.register(Amenity)
class AmenityAdmin(gis_admin.ModelAdmin):
    list_display = ("name", "code", "category", "icon", "order")
    list_filter = ("category",)
    list_editable = ("order",)


@gis_admin.register(PricingPlan)
class PricingPlanAdmin(gis_admin.ModelAdmin):
    list_display = ("property", "rental_mode", "price", "min_duration", "max_duration", "is_active")
    list_filter = ("rental_mode", "is_active")
