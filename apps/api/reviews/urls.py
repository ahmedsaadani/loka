from rest_framework.routers import SimpleRouter

from reviews.views import ReviewViewSet, StaffReviewViewSet

router = SimpleRouter()
router.register("staff", StaffReviewViewSet, basename="staff-review")
router.register("", ReviewViewSet, basename="review")

urlpatterns = router.urls
