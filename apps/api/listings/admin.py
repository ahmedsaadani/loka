from django.contrib.gis import admin as gis_admin

from listings.models import Amenity, PricingPlan, Property, PropertyAmenity, PropertyPhoto


class PropertyPhotoInline(gis_admin.TabularInline):
    model = PropertyPhoto
    extra = 0
    fields = ("order", "is_cover", "alt_text", "taken_by_team", "is_ready")
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
