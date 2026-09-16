from django.contrib import admin
from django.urls import URLPattern, URLResolver, include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from core.admin_views import ContentToWriteView, content_preview

api_v1: list[URLPattern | URLResolver] = [
    path("", include("core.urls")),
    path("auth/", include("accounts.urls")),
    path("geo/", include("geo.urls")),
    path("listings/", include("listings.urls")),
    path("availability/", include("availability.urls")),
    path("bookings/", include("bookings.urls")),
    path("leads/", include("leads.urls")),
    path("messaging/", include("messaging.urls")),
    path("schema/", SpectacularAPIView.as_view(), name="schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]

urlpatterns = [
    path(
        "admin/contenus-a-rediger/",
        ContentToWriteView.as_view(),
        name="admin-content-to-write",
    ),
    path("admin/contenus-a-rediger/apercu/", content_preview, name="admin-content-preview"),
    path("admin/", admin.site.urls),
    path("api/v1/", include((api_v1, "v1"), namespace="v1")),
]
