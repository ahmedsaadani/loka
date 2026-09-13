"""Reconstruit l'instantané public des biens publiés ou en pause (ADR 0007, données antérieures)."""

from typing import Any

from django.core.management.base import BaseCommand

from listings import services
from listings.models import Property, PropertyStatus


class Command(BaseCommand):
    help = "Reconstruit Property.published_snapshot pour les biens publiés / en pause."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--force", action="store_true", help="Recalcule même si présent")

    def handle(self, *args: Any, **options: Any) -> None:
        qs = Property.objects.filter(status__in=[PropertyStatus.PUBLISHED, PropertyStatus.PAUSED])
        if not options["force"]:
            qs = qs.filter(published_snapshot__isnull=True)
        count = 0
        for prop in qs.iterator():
            prop.published_snapshot = services.build_published_snapshot(prop)
            prop.save(update_fields=["published_snapshot", "updated_at"])
            count += 1
        self.stdout.write(self.style.SUCCESS(f"{count} instantané(s) reconstruit(s)."))
