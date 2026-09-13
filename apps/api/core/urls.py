from django.urls import path

from core.views import HealthView, StaffStatsView

urlpatterns = [
    path("health/", HealthView.as_view(), name="health"),
    path("staff/stats/", StaffStatsView.as_view(), name="staff-stats"),
]
