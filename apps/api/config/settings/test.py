from .base import *  # noqa: F401, F403
from .base import REST_FRAMEWORK

DEBUG = False
SECRET_KEY = "test-only-secret-key-0123456789abcdef0123456789abcdef"  # nosec B105 - tests
ALLOWED_HOSTS = ["*"]

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

# Stockage en mémoire : aucun appel S3 pendant les tests.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "private": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
PAYMENT_PROVIDER = "mock"
# Jamais d'appel HTTP vers le front pendant les tests (les tests dédiés mockent urlopen).
REVALIDATE_URL = ""
REVALIDATE_SECRET = ""
JWT_COOKIE_SECURE = False

# Limites larges par défaut ; les tests de rate limiting surchargent explicitement.
_base_rates = REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]
assert isinstance(_base_rates, dict)
REST_FRAMEWORK = {
    **REST_FRAMEWORK,
    "DEFAULT_THROTTLE_RATES": {key: "10000/min" for key in _base_rates},
}
