"""
Settings de base Loka. Les valeurs sensibles viennent exclusivement de l'environnement.
dev.py / prod.py / test.py surchargent ce fichier.
"""

from __future__ import annotations

import os
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlparse

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent.parent


def env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


def env_bool(key: str, default: bool = False) -> bool:
    raw = os.environ.get(key)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def env_int(key: str, default: int) -> int:
    raw = os.environ.get(key)
    return int(raw) if raw else default


def env_list(key: str, default: str = "") -> list[str]:
    return [item.strip() for item in env(key, default).split(",") if item.strip()]


# ------------------------------------------------------------------ core
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
SITE_URL = env("SITE_URL", "http://localhost:3000")
ENVIRONMENT = env("ENVIRONMENT", "dev")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "django.contrib.postgres",
    # tiers
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_filters",
    "corsheaders",
    "storages",
    # loka
    "core",
    "accounts",
    "geo",
    "listings",
    "availability",
    "bookings",
    "leads",
    "reviews",
    "notifications",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.SecurityHeadersMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ------------------------------------------------------------------ base de données
DATABASES = {
    "default": dj_database_url.config(
        env="DATABASE_URL",
        default="postgis://loka:loka@localhost:5432/loka",
        conn_max_age=60,
        conn_health_checks=True,
    )
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ------------------------------------------------------------------ auth
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 10},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ------------------------------------------------------------------ i18n
LANGUAGE_CODE = "fr"
LANGUAGES = [("fr", "Français"), ("ar", "العربية"), ("en", "English")]
TIME_ZONE = "Africa/Tunis"
USE_I18N = True
USE_TZ = True

# ------------------------------------------------------------------ static & media
STATIC_URL = "/django-static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

S3_ENDPOINT_URL = env("S3_ENDPOINT_URL", "http://localhost:9000")
S3_PUBLIC_ENDPOINT_URL = env("S3_PUBLIC_ENDPOINT_URL", S3_ENDPOINT_URL)
S3_ACCESS_KEY = env("S3_ACCESS_KEY")
S3_SECRET_KEY = env("S3_SECRET_KEY")
S3_REGION = env("S3_REGION", "us-east-1")
S3_BUCKET_PUBLIC = env("S3_BUCKET_PUBLIC", "loka-public")
S3_BUCKET_PRIVATE = env("S3_BUCKET_PRIVATE", "loka-private")
S3_PRIVATE_URL_EXPIRY_SECONDS = env_int("S3_PRIVATE_URL_EXPIRY_SECONDS", 300)

_public_host = urlparse(S3_PUBLIC_ENDPOINT_URL)
_s3_common = {
    "access_key": S3_ACCESS_KEY,
    "secret_key": S3_SECRET_KEY,
    "region_name": S3_REGION,
    "endpoint_url": S3_ENDPOINT_URL,
    "default_acl": None,
    "file_overwrite": False,
    "addressing_style": "path",
    "signature_version": "s3v4",
}
STORAGES = {
    # Bucket public : variantes WebP des photos. URLs stables, sans signature.
    "default": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            **_s3_common,
            "bucket_name": S3_BUCKET_PUBLIC,
            "querystring_auth": False,
            "custom_domain": f"{_public_host.netloc}/{S3_BUCKET_PUBLIC}",
            "url_protocol": f"{_public_host.scheme}:",
            "object_parameters": {"CacheControl": "max-age=31536000, public"},
        },
    },
    # Bucket privé : originaux, pièces d'identité, contrats.
    # URL signée uniquement (voir core.storages).
    "private": {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            **_s3_common,
            "bucket_name": S3_BUCKET_PRIVATE,
            "querystring_auth": True,
            "querystring_expire": S3_PRIVATE_URL_EXPIRY_SECONDS,
        },
    },
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

# ------------------------------------------------------------------ uploads
UPLOAD_MAX_IMAGE_BYTES = 10 * 1024 * 1024
UPLOAD_MAX_DOCUMENT_BYTES = 8 * 1024 * 1024
UPLOAD_ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
UPLOAD_ALLOWED_DOCUMENT_MIME = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
# Variantes générées en WebP par Celery (largeur, hauteur max). Jamais servir l'original.
PHOTO_VARIANTS: dict[str, tuple[int, int]] = {
    "thumb": (320, 240),
    "card": (640, 480),
    "gallery": (1280, 960),
    "og": (1200, 630),
}

# ------------------------------------------------------------------ DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": ("rest_framework.permissions.IsAuthenticated",),
    "DEFAULT_PAGINATION_CLASS": "core.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "core.exceptions.exception_handler",
    "DEFAULT_RENDERER_CLASSES": ("rest_framework.renderers.JSONRenderer",),
    "DEFAULT_THROTTLE_CLASSES": (
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ),
    "DEFAULT_THROTTLE_RATES": {
        "anon": "120/min",
        "user": "600/min",
        "auth": "10/min",
        "register": "5/hour",
        "booking_request": "10/hour",
        "lead_import": "5/hour",
        "upload": "60/hour",
    },
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Loka API",
    "DESCRIPTION": "API de la plateforme Loka - location d'hébergements vérifiés en Tunisie.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "ENUM_NAME_OVERRIDES": {
        "PropertyStatusEnum": "listings.models.PropertyStatus.choices",
        "BookingRequestStatusEnum": "bookings.models.BookingRequestStatus.choices",
        "BookingStatusEnum": "bookings.models.BookingStatus.choices",
        "LeadStatusEnum": "leads.models.LeadStatus.choices",
        "IdentityDocumentStatusEnum": "accounts.models.IdentityDocumentStatus.choices",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env_int("JWT_ACCESS_TTL_MINUTES", 15)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env_int("JWT_REFRESH_TTL_DAYS", 30)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}
JWT_REFRESH_COOKIE_NAME = env("JWT_REFRESH_COOKIE_NAME", "loka_refresh")
JWT_COOKIE_SECURE = env_bool("JWT_COOKIE_SECURE", False)
JWT_COOKIE_SAMESITE = "Lax"
JWT_COOKIE_PATH = "/api/v1/auth/"

# ------------------------------------------------------------------ CORS / CSRF
CORS_ALLOWED_ORIGINS = env_list("CORS_ALLOWED_ORIGINS", "http://localhost:3000")
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = CORS_ALLOWED_ORIGINS
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
# CSP appliquée par core.middleware.SecurityHeadersMiddleware.
# L'admin et les docs Swagger ont besoin de jsdelivr.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "img-src 'self' data: https: http://localhost:9000; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "font-src 'self' https://cdn.jsdelivr.net; "
    "frame-ancestors 'none'"
)

# ------------------------------------------------------------------ cache / celery
REDIS_URL = env("REDIS_URL", "redis://localhost:6379/0")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}
CELERY_BROKER_URL = env("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = None
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_ACKS_LATE = True
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULE = {
    "expire-booking-requests": {
        "task": "bookings.tasks.expire_pending_requests",
        "schedule": 600.0,
    },
    "remind-hosts-pending-requests": {
        "task": "bookings.tasks.remind_hosts_of_pending_requests",
        "schedule": 1800.0,
    },
    "sync-external-calendars": {
        "task": "availability.tasks.sync_all_external_calendars",
        "schedule": 3600.0,
    },
    "advance-booking-statuses": {
        "task": "bookings.tasks.advance_booking_statuses",
        "schedule": 3600.0,
    },
}

# ------------------------------------------------------------------ email
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "Loka <no-reply@loka.tn>")

# ------------------------------------------------------------------ règles métier (voir ADR 0003)
# Frais de service par mode. Nuitée : à la charge du voyageur, ajoutés au total.
# Mensuel / annuel : à la charge de l'hôte, déduits de l'acompte.
PLATFORM_FEE: dict[str, Decimal] = {
    "nightly": Decimal("0.10"),
    "monthly": Decimal("0.05"),
    "yearly": Decimal("0.03"),
}
PLATFORM_FEE_PAYER: dict[str, str] = {
    "nightly": "traveler",
    "monthly": "host",
    "yearly": "host",
}
# Acompte (montant payé sur la plateforme pour confirmer) :
# - nuitée : 30 % du total (option prudente, voir ADR 0005)
# - mensuel / annuel : un mois de loyer
BOOKING_DEPOSIT_RATE_NIGHTLY = Decimal("0.30")
# Expiration d'une demande sans réponse de l'hôte, et rappel envoyé avant.
BOOKING_REQUEST_TTL_HOURS = 48
BOOKING_REQUEST_REMINDER_HOURS = 24
# Taux EUR indicatif (1 TND -> EUR). Affichage seulement, jamais utilisé pour un paiement.
EUR_RATE = Decimal("0.295")
# Annulation par le voyageur : délai avant le début pour un remboursement de l'acompte (ADR 0005)
BOOKING_FREE_CANCELLATION_DAYS = 7

PAYMENT_PROVIDER = env("PAYMENT_PROVIDER", "mock")

# Revalidation ISR du front Next.js après publication / changement de prix (vide = désactivé).
REVALIDATE_URL = env("REVALIDATE_URL", "")
REVALIDATE_SECRET = env("REVALIDATE_SECRET", "")
# Lien de réinitialisation de mot de passe (page front), valable PASSWORD_RESET_TIMEOUT secondes.
PASSWORD_RESET_URL = env("PASSWORD_RESET_URL", f"{SITE_URL}/reinitialisation")
PASSWORD_RESET_TIMEOUT = 60 * 60

# ------------------------------------------------------------------ logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        # Journal des actions sensibles : accès documents, transitions, validations.
        "loka.audit": {"handlers": ["console"], "level": "INFO", "propagate": False},
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}
