"""
Données de démo : 3 villes, 10 quartiers, 25 biens publiés avec photos placeholder,
équipements, plans tarifaires, 4 comptes de test et quelques leads.
Idempotent : relancer ne duplique rien.
"""

from __future__ import annotations

import random
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from typing import Any

from django.contrib.gis.geos import Point
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from PIL import Image, ImageDraw

from accounts.models import HostProfile, Role, User
from geo.models import City, Governorate, Neighborhood
from leads.models import Lead, LeadSource
from listings.models import (
    Amenity,
    ConditionGrade,
    LocationPrecision,
    PricingPlan,
    Property,
    PropertyPhoto,
    PropertyStatus,
    PropertyType,
    RentalMode,
    VerificationLevel,
)
from notifications.tasks import generate_photo_variants

ACCOUNTS = [
    ("admin@loka.tn", "loka-admin", Role.ADMIN, "Amira", "Ben Salah"),
    ("staff@loka.tn", "loka-staff", Role.STAFF, "Karim", "Trabelsi"),
    ("host@loka.tn", "loka-host", Role.HOST, "Sami", "Gharbi"),
    ("traveler@loka.tn", "loka-traveler", Role.TRAVELER, "Léa", "Martin"),
]

GEO: dict[str, dict[str, Any]] = {
    "Ariana": {
        "gov": "Ariana",
        "centroid": (10.1647, 36.8625),
        "featured": True,
        "intro": (
            "Ariana attire étudiants et jeunes actifs grâce à ses campus (ESPRIT, ISG, Université de "
            "Carthage) et à sa proximité avec le Lac et le centre de Tunis. Les quartiers de Ghazela, "
            "Ennasr et Menzah offrent un large choix d'appartements meublés."
        ),
        "neighborhoods": {
            "Ghazela": (10.1875, 36.8975),
            "Ennasr": (10.1560, 36.8560),
            "Menzah 6": (10.1620, 36.8460),
            "Borj Louzir": (10.1900, 36.8840),
        },
    },
    "Tunis": {
        "gov": "Tunis",
        "centroid": (10.1815, 36.8065),
        "featured": True,
        "intro": (
            "Capitale et centre économique, Tunis concentre les locations moyenne durée pour expatriés "
            "et professionnels, du Lac 2 à La Marsa en passant par le Bardo et Mutuelleville."
        ),
        "neighborhoods": {
            "Lac 2": (10.2560, 36.8390),
            "La Marsa": (10.3250, 36.8780),
            "Bardo": (10.1400, 36.8090),
            "Mutuelleville": (10.1760, 36.8300),
        },
    },
    "Sousse": {
        "gov": "Sousse",
        "centroid": (10.6400, 35.8250),
        "featured": True,
        "intro": (
            "Sousse combine location saisonnière en bord de mer et logements étudiants près des "
            "facultés. Sahloul et Kantaoui sont les quartiers les plus demandés."
        ),
        "neighborhoods": {
            "Sahloul": (10.5950, 35.8400),
            "Kantaoui": (10.5990, 35.8900),
        },
    },
}

AMENITIES = [
    ("wifi", "Wi-Fi", "wifi", Amenity.Category.ESSENTIAL, 1),
    ("ac", "Climatisation", "snowflake", Amenity.Category.ESSENTIAL, 2),
    ("heating", "Chauffage", "flame", Amenity.Category.ESSENTIAL, 3),
    ("kitchen", "Cuisine équipée", "cooking-pot", Amenity.Category.ESSENTIAL, 4),
    ("washer", "Lave-linge", "washing-machine", Amenity.Category.COMFORT, 5),
    ("tv", "Télévision", "tv", Amenity.Category.COMFORT, 6),
    ("desk", "Espace de travail", "laptop", Amenity.Category.COMFORT, 7),
    ("balcony", "Balcon", "sun", Amenity.Category.COMFORT, 8),
    ("parking", "Parking", "car", Amenity.Category.BUILDING, 9),
    ("elevator", "Ascenseur", "arrow-up-down", Amenity.Category.BUILDING, 10),
    ("security", "Gardien / sécurité", "shield-check", Amenity.Category.SAFETY, 11),
    ("smoke_detector", "Détecteur de fumée", "siren", Amenity.Category.SAFETY, 12),
]

PROPERTY_TEMPLATES = [
    (PropertyType.STUDIO, "Studio", 0, 1, 30, 1),
    (PropertyType.APARTMENT, "S+1", 1, 1, 55, 2),
    (PropertyType.APARTMENT, "S+2", 2, 1, 85, 4),
    (PropertyType.APARTMENT, "S+3", 3, 2, 120, 6),
    (PropertyType.VILLA, "Villa", 4, 3, 220, 8),
    (PropertyType.ROOM, "Chambre", 1, 1, 18, 1),
]

ADJECTIVES = ["lumineux", "calme", "moderne", "rénové", "spacieux", "cosy", "élégant"]
FEATURES = [
    "avec balcon",
    "vue dégagée",
    "proche du métro",
    "près des facs",
    "quartier résidentiel",
    "à deux pas des commerces",
]
COLORS = ["#c96f4a", "#b5502e", "#d9a066", "#8a9a7b", "#6b8fa3", "#a37b6b", "#7f8c8d"]

DESCRIPTION = (
    "{title}. Situé à {neighborhood}, ce {kind} de {surface} m² est entièrement meublé et équipé pour "
    "un emménagement immédiat. Il comprend {bedrooms} chambre(s), {bathrooms} salle(s) de bain, une "
    "cuisine fonctionnelle et un séjour agréable. L'immeuble est bien entretenu, le voisinage calme. "
    "Idéal pour un étudiant, un jeune actif ou un séjour professionnel de quelques mois. "
    "Le bien a été visité et vérifié par l'équipe Loka : les photos correspondent à la réalité."
)

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


def placeholder_image(label: str, color: str, size: tuple[int, int] = (1600, 1200)) -> ContentFile:
    image = Image.new("RGB", size, color)
    draw = ImageDraw.Draw(image)
    draw.rectangle((40, 40, size[0] - 40, size[1] - 40), outline="#ffffff", width=6)
    draw.text((80, 80), label, fill="#ffffff")
    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=85)
    return ContentFile(buffer.getvalue(), name="placeholder.jpg")


class Command(BaseCommand):
    help = "Charge les données de démonstration Loka."

    def add_arguments(self, parser: Any) -> None:
        parser.add_argument("--properties", type=int, default=25)
        parser.add_argument(
            "--no-photos", action="store_true", help="Ne génère pas les photos (plus rapide)"
        )

    @transaction.atomic
    def handle(self, *args: Any, **options: Any) -> None:
        rng = random.Random(42)  # nosec B311 - données de démo, aucun usage cryptographique
        users = self._seed_accounts()
        cities = self._seed_geo()
        amenities = self._seed_amenities()
        count = self._seed_properties(
            rng,
            users["host@loka.tn"],
            cities,
            amenities,
            options["properties"],
            not options["no_photos"],
        )
        self._seed_leads(users["staff@loka.tn"])
        self.stdout.write(self.style.SUCCESS(f"Seed terminé : {count} biens publiés."))

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
                        "bio": "Propriétaire de plusieurs biens à Tunis et Ariana.",
                    },
                )
            users[email] = user
        return users

    def _seed_geo(self) -> dict[str, City]:
        cities: dict[str, City] = {}
        for city_name, data in GEO.items():
            gov, _ = Governorate.objects.get_or_create(
                slug=city_name.lower(), defaults={"name": data["gov"]}
            )
            city, _ = City.objects.update_or_create(
                slug=city_name.lower(),
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
                    "intro_text": data["intro"],
                },
            )
            for name, (lng, lat) in data["neighborhoods"].items():
                slug = name.lower().replace(" ", "-")
                Neighborhood.objects.update_or_create(
                    city=city,
                    slug=slug,
                    defaults={
                        "name": name,
                        "centroid": Point(lng, lat, srid=4326),
                        "seo_title": f"Location {name}, {city_name} : appartements vérifiés | Loka",
                        "seo_description": f"Appartements meublés à {name} ({city_name}) visités et validés par Loka.",
                        "intro_text": f"{name} est l'un des quartiers les plus recherchés de {city_name}.",
                    },
                )
            cities[city_name] = city
        return cities

    def _seed_amenities(self) -> list[Amenity]:
        result = []
        for code, name, icon, category, order in AMENITIES:
            amenity, _ = Amenity.objects.update_or_create(
                code=code,
                defaults={"name": name, "icon": icon, "category": category, "order": order},
            )
            result.append(amenity)
        return result

    def _seed_properties(
        self,
        rng: random.Random,
        host: User,
        cities: dict[str, City],
        amenities: list[Amenity],
        total: int,
        with_photos: bool,
    ) -> int:
        existing = Property.objects.filter(
            host=host, verification_notes__startswith="[seed]"
        ).count()
        if existing >= total:
            self.stdout.write(f"{existing} biens de démo déjà présents, rien à faire.")
            return existing
        neighborhoods = list(Neighborhood.objects.select_related("city"))
        admin = User.objects.get(email="admin@loka.tn")
        created = 0
        for index in range(existing, total):
            neighborhood = neighborhoods[index % len(neighborhoods)]
            ptype, label, bedrooms, bathrooms, surface, guests = PROPERTY_TEMPLATES[
                index % len(PROPERTY_TEMPLATES)
            ]
            adjective = ADJECTIVES[index % len(ADJECTIVES)]
            feature = FEATURES[(index * 3) % len(FEATURES)]
            title = f"{label} {adjective} {feature} à {neighborhood.name}"
            lng = neighborhood.centroid.x + rng.uniform(-0.006, 0.006)
            lat = neighborhood.centroid.y + rng.uniform(-0.005, 0.005)
            base_month = {
                PropertyType.STUDIO: 550,
                PropertyType.APARTMENT: 750 + 250 * bedrooms,
                PropertyType.VILLA: 3200,
                PropertyType.ROOM: 380,
            }[ptype]
            monthly = Decimal(base_month + rng.randrange(-100, 200, 50))
            nightly = Decimal(int(monthly / 14))
            prop = Property.objects.create(
                host=host,
                title=title[:140],
                description=DESCRIPTION.format(
                    title=title,
                    neighborhood=neighborhood.name,
                    kind=label.lower() if ptype != PropertyType.APARTMENT else "appartement",
                    surface=surface,
                    bedrooms=bedrooms,
                    bathrooms=bathrooms,
                ),
                property_type=ptype,
                rooms_label=label if label.startswith("S+") else "",
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                surface_m2=surface,
                floor=rng.randrange(0, 6),
                has_elevator=rng.random() > 0.4,
                furnished=True,
                city=neighborhood.city,
                neighborhood=neighborhood,
                address_private=f"{rng.randrange(1, 90)} rue {rng.choice(['des Jasmins', 'Habib Bourguiba', 'de Carthage', 'Ibn Khaldoun'])}, {neighborhood.name}",
                location=Point(lng, lat, srid=4326),
                location_precision=LocationPrecision.APPROXIMATE,
                max_guests=guests,
                status=PropertyStatus.PUBLISHED,
                verification_level=VerificationLevel.SELECTION
                if index % 5 == 0
                else VerificationLevel.VERIFIED,
                verified_at=timezone.now() - timedelta(days=rng.randrange(3, 90)),
                verified_by=admin,
                verification_notes="[seed] bien de démonstration",
                condition_grade=rng.choice(list(ConditionGrade.values)),
                charges_included=rng.random() > 0.5,
                monthly_charges_estimate=Decimal(rng.choice([60, 80, 100, 120])),
                deposit_months=rng.choice([1, 1, 2]),
                min_lease_months=rng.choice([1, 1, 3, 6]),
                distance_notes=rng.choice(
                    [
                        {"ESPRIT": "8 min à pied", "Métro Ligne 2": "5 min"},
                        {"Centre-ville": "15 min en voiture", "Supermarché": "3 min à pied"},
                        {"Plage": "10 min à pied", "Faculté de médecine": "12 min en bus"},
                    ]
                ),
                house_rules={"smoking": False, "pets": rng.random() > 0.7, "parties": False},
                published_at=timezone.now() - timedelta(days=rng.randrange(1, 60)),
            )
            prop.amenities.set(rng.sample(amenities, k=rng.randrange(4, 9)))
            PricingPlan.objects.create(
                property=prop,
                rental_mode=RentalMode.MONTHLY,
                price=monthly,
                min_duration=prop.min_lease_months,
                max_duration=11,
            )
            if ptype != PropertyType.ROOM:
                PricingPlan.objects.create(
                    property=prop,
                    rental_mode=RentalMode.NIGHTLY,
                    price=nightly,
                    min_duration=2,
                    max_duration=30,
                )
            if index % 3 == 0:
                PricingPlan.objects.create(
                    property=prop, rental_mode=RentalMode.YEARLY, price=monthly - Decimal(100)
                )
            if with_photos:
                for order in range(1, 5):
                    photo = PropertyPhoto(
                        property=prop,
                        order=order,
                        is_cover=order == 1,
                        alt_text=f"{title} - photo {order}",
                        taken_by_team=True,
                        width=1600,
                        height=1200,
                    )
                    photo.original.save(
                        "seed.jpg",
                        placeholder_image(
                            f"{title} #{order}", COLORS[(index + order) % len(COLORS)]
                        ),
                        save=False,
                    )
                    photo.save()
                    generate_photo_variants(photo.pk)
            created += 1
        return existing + created

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
