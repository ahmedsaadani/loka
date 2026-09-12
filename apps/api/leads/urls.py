from rest_framework.routers import SimpleRouter

from leads.views import LeadViewSet

router = SimpleRouter()
router.register("", LeadViewSet, basename="lead")

urlpatterns = router.urls
