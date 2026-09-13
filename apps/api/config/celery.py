import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("loka")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
# Le module core.tasks_backup n'est pas nommé `tasks` : découverte explicite.
app.autodiscover_tasks(["core"], related_name="tasks_backup")
