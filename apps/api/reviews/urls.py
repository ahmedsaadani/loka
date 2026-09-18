from rest_framework.routers import SimpleRouter

from reviews.views import ReviewViewSet

router = SimpleRouter()
router.register("", ReviewViewSet, basename="review")

urlpatterns = router.urls
