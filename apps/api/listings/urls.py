from rest_framework.routers import SimpleRouter

from listings.views import (
    AmenityListView,
    HostPropertyViewSet,
    PublicPropertyViewSet,
    StaffPropertyViewSet,
)

router = SimpleRouter()
router.register("properties", PublicPropertyViewSet, basename="property")
router.register("amenities", AmenityListView, basename="amenity")
router.register("host/properties", HostPropertyViewSet, basename="host-property")
router.register("staff/properties", StaffPropertyViewSet, basename="staff-property")

urlpatterns = router.urls
