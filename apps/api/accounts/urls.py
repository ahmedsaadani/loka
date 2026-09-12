from django.urls import path
from rest_framework.routers import SimpleRouter

from accounts.views import (
    IdentityDocumentViewSet,
    LoginView,
    LogoutView,
    MeView,
    RefreshView,
    RegisterView,
)

router = SimpleRouter()
router.register("identity-documents", IdentityDocumentViewSet, basename="identity-document")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    *router.urls,
]
