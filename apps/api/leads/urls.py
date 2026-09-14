from django.urls import path
from rest_framework.routers import SimpleRouter

from leads.views import LeadViewSet, OwnerContactView

router = SimpleRouter()
router.register("", LeadViewSet, basename="lead")

urlpatterns = [
    path("owner-contact/", OwnerContactView.as_view(), name="owner-contact"),
    *router.urls,
]
