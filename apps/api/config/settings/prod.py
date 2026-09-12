from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F401, F403
from .base import ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS, SECRET_KEY

DEBUG = False

if not SECRET_KEY or SECRET_KEY.startswith("dev-only") or len(SECRET_KEY) < 50:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY doit être défini (>= 50 caractères) en production."
    )
if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
    raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS doit être une liste stricte en production.")
if any(origin.startswith("http://") for origin in CORS_ALLOWED_ORIGINS):
    raise ImproperlyConfigured("CORS_ALLOWED_ORIGINS doit être en HTTPS en production.")

# Derrière nginx / load balancer
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 60 * 60 * 24 * 365
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
JWT_COOKIE_SECURE = True

STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
}
