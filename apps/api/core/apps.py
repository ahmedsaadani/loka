from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"
    verbose_name = "Socle"

    def ready(self) -> None:
        from django.conf import settings

        from core import checks

        if settings.ENVIRONMENT == "prod":
            checks.warn_if_placeholders_remain()
