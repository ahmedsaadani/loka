from django.contrib.gis import admin as gis_admin

from geo.models import City, Governorate, Neighborhood


@gis_admin.register(Governorate)
class GovernorateAdmin(gis_admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@gis_admin.register(City)
class CityAdmin(gis_admin.GISModelAdmin):
    list_display = ("name", "governorate", "slug", "is_featured")
    list_filter = ("governorate", "is_featured")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)


@gis_admin.register(Neighborhood)
class NeighborhoodAdmin(gis_admin.GISModelAdmin):
    list_display = ("name", "city", "slug")
    list_filter = ("city",)
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name", "city__name")
