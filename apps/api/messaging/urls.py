from rest_framework.routers import SimpleRouter

from messaging.views import ConversationViewSet, UnreadCountView

router = SimpleRouter()
router.register("conversations", ConversationViewSet, basename="conversation")
router.register("unread", UnreadCountView, basename="unread")

urlpatterns = router.urls
