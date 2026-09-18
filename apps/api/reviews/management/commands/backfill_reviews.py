"""Ajoute des avis de démonstration aux biens publiés qui n'en ont pas encore.

Idempotent : un bien qui a déjà des avis est ignoré. Sûr à lancer à chaque déploiement
(utilisé par render-start.sh pour les bases déjà peuplées où `seed` ne se relance pas).
"""

from __future__ import annotations

import random
from typing import Any

from django.core.management.base import BaseCommand

from listings.models import Property, PropertyStatus
from reviews.seeding import ensure_reviewers, seed_reviews_for_property


class Command(BaseCommand):
    help = "Crée des avis de démonstration pour les biens publiés qui n'en ont pas."

    def handle(self, *args: Any, **options: Any) -> None:
        rng = random.Random(2026)  # noqa: S311  # nosec B311 - données de démo, non cryptographique
        reviewers = ensure_reviewers()
        published = Property.objects.filter(status=PropertyStatus.PUBLISHED).prefetch_related(
            "pricing_plans"
        )
        total_reviews = 0
        touched = 0
        for prop in published:
            created = seed_reviews_for_property(prop, rng, reviewers)
            if created:
                touched += 1
                total_reviews += created
        self.stdout.write(
            self.style.SUCCESS(
                f"Backfill terminé : {total_reviews} avis créés sur {touched} bien(s)."
            )
        )
