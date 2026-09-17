from django.urls import path
from rest_framework.routers import SimpleRouter

from accounts.views import (
    FacebookLoginView,
    GoogleLoginView,
    IdentityDocumentViewSet,
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RefreshView,
    RegisterView,
)

router = SimpleRouter()
router.register("identity-documents", IdentityDocumentViewSet, basename="identity-document")

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("google/", GoogleLoginView.as_view(), name="google-login"),
    path("facebook/", FacebookLoginView.as_view(), name="facebook-login"),
    path("refresh/", RefreshView.as_view(), name="refresh"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("me/", MeView.as_view(), name="me"),
    path("password/reset/", PasswordResetRequestView.as_view(), name="password-reset"),
    path(
        "password/reset/confirm/", PasswordResetConfirmView.as_view(), name="password-reset-confirm"
    ),
    path("password/change/", PasswordChangeView.as_view(), name="password-change"),
    *router.urls,
]
