from django.urls import path
from rest_framework.routers import SimpleRouter

from bookings.views import (
    HostBookingViewSet,
    HostRequestViewSet,
    KonnectPaymentWebhookView,
    MockPaymentSignView,
    MockPaymentWebhookView,
    StaffBookingViewSet,
    StaffRequestViewSet,
    TravelerBookingViewSet,
    TravelerRequestViewSet,
)

router = SimpleRouter()
router.register("requests", TravelerRequestViewSet, basename="request")
router.register("bookings", TravelerBookingViewSet, basename="booking")
router.register("host/requests", HostRequestViewSet, basename="host-request")
router.register("host/bookings", HostBookingViewSet, basename="host-booking")
router.register("staff/requests", StaffRequestViewSet, basename="staff-request")
router.register("staff/bookings", StaffBookingViewSet, basename="staff-booking")

urlpatterns = [
    path("webhooks/mock/", MockPaymentWebhookView.as_view(), name="mock-webhook"),
    path("webhooks/konnect/", KonnectPaymentWebhookView.as_view(), name="konnect-webhook"),
    path("mock/sign/<str:provider_ref>/", MockPaymentSignView.as_view(), name="mock-sign"),
    *router.urls,
]
