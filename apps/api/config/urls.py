from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

api_v1: list[URLPattern | URLResolver] = [
    path("", include("core.urls")),
    path("auth/", include("accounts.urls")),
    path("geo/", include("geo.urls")),
    path("listings/", include("listings.urls")),
    path("availability/", include("availability.urls")),
    path("bookings/", include("bookings.urls")),
    path("leads/", include("leads.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include((api_v1, "v1"), namespace="v1")),
]
