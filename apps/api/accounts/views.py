from __future__ import annotations

import contextlib
from datetime import timedelta
from typing import Any, Literal, cast

from django.conf import settings
from django.contrib.auth import authenticate
from django.db.models import QuerySet
from django.http import HttpResponse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed, NotAuthenticated
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from accounts import services
from accounts.models import IdentityDocument, IdentityDocumentStatus, User
from accounts.serializers import (
    AccessTokenSerializer,
    IdentityDocumentSerializer,
    IdentityDocumentStaffSerializer,
    IdentityDocumentUploadSerializer,
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    RejectSerializer,
    SignedUrlSerializer,
    UserSerializer,
    UserUpdateSerializer,
)
from core.audit import log_sensitive_access
from core.auth import current_user
from core.models import SensitiveAccessLog
from core.permissions import IsStaff, is_staff_user
from core.storages import signed_private_url

SAMESITE: Literal["Lax"] = "Lax"


def _set_refresh_cookie(response: Response, refresh: RefreshToken) -> None:
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        str(refresh),
        max_age=int(cast(timedelta, settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"]).total_seconds()),
        httponly=True,
        secure=settings.JWT_COOKIE_SECURE,
        samesite=SAMESITE,
        path=settings.JWT_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: HttpResponse) -> None:
    response.delete_cookie(
        settings.JWT_REFRESH_COOKIE_NAME,
        path=settings.JWT_COOKIE_PATH,
        samesite=SAMESITE,
    )


def _token_response(user: User, http_status: int = status.HTTP_200_OK) -> Response:
    refresh = RefreshToken.for_user(user)
    response = Response(
        {"access": str(refresh.access_token), "user": UserSerializer(user).data},
        status=http_status,
    )
    _set_refresh_cookie(response, refresh)
    return response


class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "register"

    @extend_schema(request=RegisterSerializer, responses={201: AccessTokenSerializer})
    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.register_user(**serializer.validated_data)
        return _token_response(user, status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(request=LoginSerializer, responses={200: AccessTokenSerializer})
    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request=request._request,
            username=serializer.validated_data["email"].lower(),
            password=serializer.validated_data["password"],
        )
        if user is None:
            raise AuthenticationFailed(
                "Email ou mot de passe incorrect.", code="invalid_credentials"
            )
        return _token_response(user)  # authenticate renvoie AbstractBaseUser


class RefreshView(APIView):
    """Rotation du refresh token (cookie httpOnly) avec blacklist de l'ancien."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "refresh"

    @extend_schema(request=None, responses={200: AccessTokenSerializer})
    def post(self, request: Request) -> Response:
        raw = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if not raw:
            raise NotAuthenticated("Session expirée.", code="refresh_missing")
        try:
            old = RefreshToken(cast(Any, raw))  # simplejwt accepte une chaîne encodée
            user = User.objects.get(pk=old["user_id"], is_active=True)
            old.blacklist()
        except (TokenError, User.DoesNotExist):
            response = Response(
                {"detail": "Session expirée.", "code": "refresh_invalid"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
            _clear_refresh_cookie(response)
            return response
        return _token_response(user)


class LogoutView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(request=None, responses={204: None})
    def post(self, request: Request) -> Response:
        raw = request.COOKIES.get(settings.JWT_REFRESH_COOKIE_NAME)
        if raw:
            with contextlib.suppress(TokenError):
                RefreshToken(cast(Any, raw)).blacklist()
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _clear_refresh_cookie(response)
        return response


class PasswordResetRequestView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(request=PasswordResetRequestSerializer, responses={202: None})
    def post(self, request: Request) -> Response:
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.request_password_reset(serializer.validated_data["email"])
        return Response(status=status.HTTP_202_ACCEPTED)


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    @extend_schema(request=PasswordResetConfirmSerializer, responses={200: AccessTokenSerializer})
    def post(self, request: Request) -> Response:
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = services.confirm_password_reset(**serializer.validated_data)
        return _token_response(user)


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=PasswordChangeSerializer, responses={204: None})
    def post(self, request: Request) -> Response:
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.change_password(current_user(request), **serializer.validated_data)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserSerializer})
    def get(self, request: Request) -> Response:
        return Response(UserSerializer(current_user(request)).data)

    @extend_schema(request=UserUpdateSerializer, responses={200: UserSerializer})
    def patch(self, request: Request) -> Response:
        serializer = UserUpdateSerializer(current_user(request), data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(current_user(request)).data)


class IdentityDocumentViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet[IdentityDocument]
):
    """
    Documents d'identité. L'utilisateur voit les siens, le staff voit tout.
    Le fichier n'est jamais exposé directement : /download/ renvoie une URL signée courte.
    """

    permission_classes = [IsAuthenticated]
    lookup_field = "public_id"
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get_queryset(self) -> QuerySet[IdentityDocument]:
        if getattr(self, "swagger_fake_view", False):
            return IdentityDocument.objects.none()
        qs = IdentityDocument.objects.select_related("user")
        if is_staff_user(self.request.user):
            status_filter = self.request.query_params.get("status")
            return qs.filter(status=status_filter) if status_filter else qs
        return qs.filter(user=current_user(self.request))

    def get_serializer_class(self) -> type[Any]:
        if is_staff_user(self.request.user):
            return IdentityDocumentStaffSerializer
        return IdentityDocumentSerializer

    @extend_schema(
        request=IdentityDocumentUploadSerializer, responses={201: IdentityDocumentSerializer}
    )
    def create(self, request: Request) -> Response:
        serializer = IdentityDocumentUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        document = services.submit_identity_document(
            current_user(request),
            doc_type=serializer.validated_data["doc_type"],
            upload=serializer.validated_data["file"],
        )
        return Response(IdentityDocumentSerializer(document).data, status=status.HTTP_201_CREATED)

    @extend_schema(responses={200: SignedUrlSerializer})
    @action(detail=True, methods=["get"])
    def download(self, request: Request, public_id: str | None = None) -> Response:
        document = self.get_object()
        log_sensitive_access(request._request, SensitiveAccessLog.Kind.IDENTITY_DOCUMENT, document)
        return Response(
            {
                "url": signed_private_url(document.file.name),
                "expires_in": settings.S3_PRIVATE_URL_EXPIRY_SECONDS,
            }
        )

    @extend_schema(request=None, responses={200: IdentityDocumentStaffSerializer})
    @action(detail=True, methods=["post"], permission_classes=[IsStaff])
    def approve(self, request: Request, public_id: str | None = None) -> Response:
        document = self.get_object()
        services.approve_identity_document(document, by=current_user(request))
        return Response(IdentityDocumentStaffSerializer(document).data)

    @extend_schema(
        request=RejectSerializer,
        responses={
            200: IdentityDocumentStaffSerializer,
            409: OpenApiResponse(description="Transition interdite"),
        },
    )
    @action(detail=True, methods=["post"], permission_classes=[IsStaff])
    def reject(self, request: Request, public_id: str | None = None) -> Response:
        document = self.get_object()
        serializer = RejectSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.reject_identity_document(
            document,
            by=current_user(request),
            reason=serializer.validated_data["reason"],
        )
        return Response(IdentityDocumentStaffSerializer(document).data)

    @extend_schema(responses={200: IdentityDocumentStaffSerializer(many=True)})
    @action(detail=False, methods=["get"], permission_classes=[IsStaff])
    def pending(self, request: Request) -> Response:
        qs = IdentityDocument.objects.select_related("user").filter(
            status=IdentityDocumentStatus.PENDING
        )
        page = self.paginate_queryset(qs)
        serializer = IdentityDocumentStaffSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)
