"""
Données de démonstration : 4 villes, 13 quartiers, 33 biens publiés (25 appartements et
studios, 5 villas, 3 chambres en colocation) avec de vraies photos libres de droits,
équipements, plans tarifaires, 4 comptes de test et quelques leads.

Les photos proviennent de la banque locale `seed/photos/` (constituée par
`scripts/fetch_seed_photos.py`, crédits dans `seed/photos/CREDITS.md`) et passent par le
pipeline réel : validation et ré-encodage, envoi de l'original dans le bucket privé,
variantes WebP générées par Celery.

Idempotent : chaque bien est identifié par sa clé de catalogue ; relancer ne duplique rien.
`--reset` supprime les biens de démo (et leurs fichiers) avant de les recréer.
"""

from __future__ import annotations

import json
import random
import time
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from django.conf import settings
from django.contrib.gis.geos import Point
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import ProtectedError
from django.utils import timezone
from slugify import slugify

from accounts.models import HostProfile, Role, User
from core.seed_catalog import AMENITIES, GEO, PHOTO_ALT, PHOTO_PLANS, PROPERTIES, SeedProperty
from core.storages import public_storage
from geo.models import City, Governorate, Neighborhood
from leads.models import Lead, LeadSource
from listings import services
from listings.models import (
    Amenity,
    LocationPrecision,
    PricingPlan,
    Property,
    PropertyPhoto,
    PropertyStatus,
    RentalMode,
)

SEED_TAG = "[seed]"
PHOTOS_DIR = Path(settings.BASE_DIR) / "seed" / "photos"
MANIFEST = PHOTOS_DIR / "manifest.json"

ACCOUNTS = [
    ("admin@loka.tn", "loka-admin", Role.ADMIN, "Amira", "Ben Salah"),
    ("staff@loka.tn", "loka-staff", Role.STAFF, "Karim", "Trabelsi"),
    ("host@loka.tn", "loka-host", Role.HOST, "Sami", "Gharbi"),
    ("traveler@loka.tn", "loka-traveler", Role.TRAVELER, "Léa", "Martin"),
]

STREETS = [
    "rue des Jasmins",
    "avenue Habib Bourguiba",
    "rue de Carthage",
    "rue Ibn Khaldoun",
    "rue des Oliviers",
]

LEADS = [
    (
        LeadSource.TAYARA,
        "https://www.tayara.tn/item/demo-1",
        "S+2 meublé Ennasr 2",
        950,
        "Ariana",
        "+21620111222",
    ),
    (
        LeadSource.MUBAWAB,
        "https://www.mubawab.tn/fr/a/demo-2",
        "Studio Lac 2 vue lac",
        1100,
        "Tunis",
        "+21622333444",
    ),
    (
        LeadSource.FACEBOOK,
        "https://www.facebook.com/groups/demo/posts/3",
        "Villa Kantaoui 4 chambres",
        3500,
        "Sousse",
        "+21655666777",
    ),
    (LeadSource.MANUAL, "", "Chambre étudiante Ghazela", 350, "Ariana", "+21699888777"),
]


class PhotoBank:
    """Banque locale de photos par catégorie, distribuée de façon déterministe."""

    def __init__(self, rng: random.Random) -> None:
        if not MANIFEST.exists():
            raise CommandError(
                f"Banque de photos absente ({MANIFEST}). Lancez `python scripts/fetch_seed_photos.py` "
                "à la racine du dépôt, ou relancez le seed avec --no-photos."
            )
        entries = json.loads(MANIFEST.read_text(encoding="utf-8"))
        self.by_category: dict[str, list[dict[str, Any]]] = {}
        for entry in entries:
            self.by_category.setdefault(entry["category"], []).append(entry)
        for files in self.by_category.values():
            rng.shuffle(files)
        self.cursor: dict[str, int] = dict.fromkeys(self.by_category, 0)
        missing = [
            e["file"]
            for files in self.by_category.values()
            for e in files
            if not (PHOTOS_DIR / e["file"]).exists()
        ]
        if missing:
            raise CommandError(
                f"{len(missing)} photo(s) listée(s) dans manifest.json sont absentes "
                f"(ex. {missing[0]}). Relancez scripts/fetch_seed_photos.py."
            )

    def take(self, category: str, exclude: set[str]) -> dict[str, Any]:
        files = self.by_category.get(category)
        if not files:
            raise CommandError(f"Aucune photo de catégorie « {category} » dans la banque.")
        for _ in range(len(files)):
            entry = files[self.cursor[category] % len(files)]
            self.cursor[category] += 1
            if entry["file"] not in exclude:
                return entry
        return files[self.cursor[category] % len(files)]


def _seed_rating(rng: random.Random, grade: str) -> Decimal:
    """Note moyenne réaliste, un peu plus haute pour les biens en meilleur état."""
    base = {"basic": 4.0, "good": 4.4, "excellent": 4.7}.get(grade, 4.4)
    return Decimal(str(round(min(5.0, base + rng.uniform(-0.3, 0.3)), 1)))


class Command(BaseCommand):
    help = "Charge les données de démonstration Loka."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument(
            "--properties",
            type=int,
            default=None,
            help="Nombre maximal de biens du catalogue à créer (défaut : tous)",
        )
        parser.add_argument(
            "--no-photos", action="store_true", help="Ne charge pas les photos (plus rapide)"
        )
        parser.add_argument(
            "--reset", action="store_true", help="Supprime d'abord les biens de démo existants"
        )
        parser.add_argument(
            "--wait-variants",
            type=int,
            default=180,
            help="Attente maximale (s) des variantes WebP générées par Celery ; 0 pour ne pas attendre",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        rng = random.Random(42)  # nosec B311 - données de démo, aucun usage cryptographique
        with transaction.atomic():
            users = self._seed_accounts()
            self._seed_geo()
            amenities = self._seed_amenities()
            self._seed_leads(users["staff@loka.tn"])
            self._seed_site_content()
        host = users["host@loka.tn"]
        if options["reset"]:
            self._reset_properties(host)
        with_photos = not options["no_photos"]
        bank = PhotoBank(rng) if with_photos else None
        limit = options["properties"]
        catalog = PROPERTIES[:limit] if limit else PROPERTIES
        created = 0
        for index, spec in enumerate(catalog):
            if self._create_property(index, spec, rng, host, amenities, bank):
                created += 1
        if with_photos and options["wait_variants"]:
            self._wait_for_variants(host, options["wait_variants"])
        call_command("rebuild_snapshots", "--force")
        self._revalidate_front()
        total = Property.objects.filter(host=host, verification_notes__startswith=SEED_TAG).count()
        self.stdout.write(
            self.style.SUCCESS(f"Seed terminé : {created} bien(s) créé(s), {total} biens de démo.")
        )

    def _revalidate_front(self) -> None:
        """Purge le cache des pages publiques du front (accueil, villes, quartiers, recherche)."""
        from core.tasks import enqueue
        from notifications.tasks import revalidate_front

        if not settings.REVALIDATE_URL:
            self.stdout.write(
                "REVALIDATE_URL non défini : le cache du front n'est pas purgé "
                "(redémarrez le serveur Next ou appelez /api/revalidate)."
            )
            return
        paths = ["/", "/recherche"]
        tags: list[str] = []
        for city in City.objects.prefetch_related("neighborhoods"):
            paths.append(f"/location/{city.slug}")
            tags.append(f"city:{city.slug}")
            paths.extend(f"/location/{city.slug}/{n.slug}" for n in city.neighborhoods.all())
        enqueue(revalidate_front, paths, tags)

    # ------------------------------------------------------------------ comptes, géo

    def _seed_accounts(self) -> dict[str, User]:
        users: dict[str, User] = {}
        for email, password, role, first, last in ACCOUNTS:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "role": role,
                    "first_name": first,
                    "last_name": last,
                    "is_staff": role == Role.ADMIN,
                    "is_superuser": role == Role.ADMIN,
                    "is_identity_verified": role != Role.TRAVELER,
                    "phone": "+21620000000",
                },
            )
            if created:
                user.set_password(password)
                user.save(update_fields=["password"])
            if role == Role.HOST:
                HostProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        "display_name": f"{first} {last}",
                        "bio": "Propriétaire de plusieurs biens à Tunis, Ariana, Sousse et Hammamet.",
                    },
                )
            users[email] = user
        return users

    def _seed_geo(self) -> None:
        for city_name, data in GEO.items():
            gov, _ = Governorate.objects.get_or_create(
                slug=slugify(data["gov"]), defaults={"name": data["gov"]}
            )
            city, _ = City.objects.update_or_create(
                slug=slugify(city_name),
                defaults={
                    "governorate": gov,
                    "name": city_name,
                    "centroid": Point(data["centroid"][0], data["centroid"][1], srid=4326),
                    "is_featured": data["featured"],
                    "seo_title": f"Location appartement meublé {city_name} : biens vérifiés | Loka",
                    "seo_description": (
                        f"Studios, S+1, S+2 et villas à louer à {city_name}, à la nuit, au mois ou à l'année. "
                        "Chaque bien est visité et validé par l'équipe Loka."
                    ),
                    "intro_text": (
                        "[À RÉDIGER] Texte d'introduction de la page ville, "
                        "à rédiger dans l'admin (Géographie > Villes)."
                    ),
                },
            )
            for name, (lng, lat) in data["neighborhoods"].items():
                Neighborhood.objects.update_or_create(
                    city=city,
                    slug=slugify(name),
                    defaults={
                        "name": name,
                        "centroid": Point(lng, lat, srid=4326),
                        "seo_title": f"Location {name}, {city_name} : appartements vérifiés | Loka",
                        "seo_description": (
                            f"Appartements meublés à {name} ({city_name}) visités et validés par Loka."
                        ),
                        "intro_text": (
                            f"[À RÉDIGER] Présentation du quartier {name} ({city_name}), "
                            "à rédiger dans l'admin."
                        ),
                    },
                )

    def _seed_amenities(self) -> dict[str, Amenity]:
        result: dict[str, Amenity] = {}
        for code, name, icon, category, order in AMENITIES:
            amenity, _ = Amenity.objects.update_or_create(
                code=code,
                defaults={"name": name, "icon": icon, "category": category, "order": order},
            )
            result[code] = amenity
        return result

    # ------------------------------------------------------------------ biens

    def _reset_properties(self, host: User) -> None:
        qs = Property.objects.filter(host=host, verification_notes__startswith=SEED_TAG)
        storage = public_storage()
        count = 0
        retired = 0
        for prop in qs:
            for photo in prop.photos.all():
                for name in settings.PHOTO_VARIANTS:
                    key = f"photos/{prop.pk}/{photo.public_id}_{name}.webp"
                    if storage.exists(key):
                        storage.delete(key)
                photo.original.delete(save=False)
            try:
                with transaction.atomic():
                    prop.delete()
            except ProtectedError:
                # Des demandes de réservation (tests, démos) pointent sur ce bien : on le retire
                # du site sans casser l'historique.
                prop.photos.all().delete()
                prop.status = PropertyStatus.DRAFT
                prop.published_snapshot = None
                prop.verification_notes = prop.verification_notes.replace(
                    SEED_TAG, "[seed-retired]", 1
                )
                prop.save(
                    update_fields=[
                        "status",
                        "published_snapshot",
                        "verification_notes",
                        "updated_at",
                    ]
                )
                retired += 1
                continue
            count += 1
        self.stdout.write(
            f"{count} bien(s) de démo supprimé(s), {retired} retiré(s) (réservations liées)."
        )

    def _create_property(
        self,
        index: int,
        spec: SeedProperty,
        rng: random.Random,
        host: User,
        amenities: dict[str, Amenity],
        bank: PhotoBank | None,
    ) -> bool:
        tag = f"{SEED_TAG} {spec['key']}"
        if Property.objects.filter(host=host, verification_notes=tag).exists():
            return False
        neighborhood = Neighborhood.objects.select_related("city").get(
            city__slug=slugify(spec["city"]), slug=slugify(spec["neighborhood"])
        )
        admin = User.objects.get(email="admin@loka.tn")
        lng = neighborhood.centroid.x + rng.uniform(-0.006, 0.006)
        lat = neighborhood.centroid.y + rng.uniform(-0.005, 0.005)
        with transaction.atomic():
            prop = Property.objects.create(
                host=host,
                title=spec["title"][:140],
                description=spec["description"],
                property_type=spec["type"],
                rooms_label=spec["label"],
                bedrooms=spec["bedrooms"],
                bathrooms=spec["bathrooms"],
                surface_m2=spec["surface"],
                floor=spec["floor"],
                has_elevator=spec["elevator"],
                furnished=True,
                city=neighborhood.city,
                neighborhood=neighborhood,
                address_private=f"{rng.randrange(1, 90)} {rng.choice(STREETS)}, {neighborhood.name}",
                location=Point(lng, lat, srid=4326),
                location_precision=LocationPrecision.APPROXIMATE,
                max_guests=spec["guests"],
                status=PropertyStatus.PUBLISHED,
                verification_level=spec["level"],
                verified_at=timezone.now() - timedelta(days=rng.randrange(3, 90)),
                verified_by=admin,
                verification_notes=tag,
                condition_grade=spec["grade"],
                charges_included=spec["charges_included"],
                monthly_charges_estimate=Decimal(spec["charges"]),
                deposit_months=spec["deposit"],
                min_lease_months=spec["min_lease"],
                distance_notes=spec["distances"],
                house_rules=spec["rules"],
                published_at=timezone.now() - timedelta(days=rng.randrange(1, 60), hours=index),
                rating=_seed_rating(rng, spec["grade"]),
                review_count=rng.randrange(4, 90),
            )
            prop.amenities.set([amenities[code] for code in spec["amenities"]])
            if spec["monthly"] is not None:
                PricingPlan.objects.create(
                    property=prop,
                    rental_mode=RentalMode.MONTHLY,
                    price=Decimal(spec["monthly"]),
                    min_duration=spec["min_lease"],
                    max_duration=11,
                )
            if spec["nightly"] is not None:
                PricingPlan.objects.create(
                    property=prop,
                    rental_mode=RentalMode.NIGHTLY,
                    price=Decimal(spec["nightly"]),
                    min_duration=3 if spec["type"] == "villa" else 2,
                    max_duration=30,
                )
            if spec["yearly"] is not None:
                PricingPlan.objects.create(
                    property=prop, rental_mode=RentalMode.YEARLY, price=Decimal(spec["yearly"])
                )
            if bank is not None:
                self._attach_photos(prop, spec, bank, index)
        self.stdout.write(f"  + {prop.title}")
        return True

    def _attach_photos(
        self, prop: Property, spec: SeedProperty, bank: PhotoBank, index: int
    ) -> None:
        used: set[str] = set()
        for position, category in enumerate(PHOTO_PLANS[spec["plan"]]):
            entry = bank.take(category, used)
            used.add(entry["file"])
            alts = PHOTO_ALT[category]
            alt = alts[(index + position) % len(alts)]
            data = (PHOTOS_DIR / entry["file"]).read_bytes()
            upload = SimpleUploadedFile(entry["file"], data, content_type="image/jpeg")
            # Pipeline réel : validation + ré-encodage, original privé, variantes WebP via Celery.
            services.add_photo(prop, upload=upload, alt_text=alt, taken_by_team=True)

    def _wait_for_variants(self, host: User, timeout: int) -> None:
        if settings.CELERY_TASK_ALWAYS_EAGER:
            return
        pending = PropertyPhoto.objects.filter(
            property__host=host, property__verification_notes__startswith=SEED_TAG, variants={}
        )
        deadline = time.monotonic() + timeout
        remaining = pending.count()
        while remaining and time.monotonic() < deadline:
            self.stdout.write(f"  … {remaining} variante(s) WebP en attente du worker Celery")
            time.sleep(3)
            remaining = pending.count()
        if remaining:
            self.stderr.write(
                self.style.WARNING(
                    f"{remaining} photo(s) sans variantes après {timeout} s : le worker Celery "
                    "tourne-t-il ? Les variantes seront générées dès qu'il traitera la file."
                )
            )

    # ------------------------------------------------------------------ leads, contenus

    def _seed_leads(self, staff: User) -> None:
        for source, url, title, price, city, phone in LEADS:
            if url and Lead.objects.filter(source_url=url).exists():
                continue
            if not url and Lead.objects.filter(title=title).exists():
                continue
            Lead.objects.create(
                source=source,
                source_url=url,
                title=title,
                price=Decimal(price),
                city=city,
                phone=phone,
                assigned_to=staff,
            )

    def _seed_site_content(self) -> None:
        from core.models import SiteContent

        pages = {
            "cgu": "Conditions d'utilisation",
            "confidentialite": "Politique de confidentialité",
            "contact": "Contact",
        }
        for key, title in pages.items():
            SiteContent.objects.get_or_create(
                key=key,
                defaults={
                    "title": title,
                    "body": (
                        f"## {title}\n\n[À RÉDIGER] Ce texte est un espace réservé. "
                        "Rédigez le contenu définitif dans l'admin (Socle > Contenus du site) "
                        "et faites-le valider par un conseil juridique avant la mise en production."
                    ),
                },
            )
