from .base import *  # noqa: F401, F403
from .base import env, env_bool

DEBUG = env_bool("DJANGO_DEBUG", True)
SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-only-insecure-secret-key")
ALLOWED_HOSTS = ["*"]

# Emails en console, cookies non sécurisés (HTTP local).
JWT_COOKIE_SECURE = False
