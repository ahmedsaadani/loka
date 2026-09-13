from django.urls import path

from core.views import HealthView, SiteContentView, StaffStatsView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("staff/stats/", StaffStatsView.as_view(), name="staff-stats"),
    path("content/<slug:key>/", SiteContentView.as_view(), name="site-content"),
]
