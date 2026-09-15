from __future__ import annotations

import builtins
from typing import Any, ClassVar

from django.conf import settings
from django.contrib.gis.db import models as gis_models
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone
from slugify import slugify

from core.models import PublicIdModel, TimeStampedModel
from core.storages import generated_name, private_storage
from geo.models import City, Neighborhood


class PropertyType(models.TextChoices):
    STUDIO = "studio", "Studio"
    APARTMENT = "apartment", "Appartement"
    VILLA = "villa", "Villa"
    ROOM = "room_in_shared_flat", "Chambre en colocation"


class PropertyStatus(models.TextChoices):
    DRAFT = "draft", "Brouillon"
    PENDING_REVIEW = "pending_review", "En attente de validation"
    NEEDS_VISIT = "needs_visit", "Visite à planifier"
    PUBLISHED = "published", "Publié"
    PAUSED = "paused", "En pause"
    REJECTED = "rejected", "Rejeté"


class VerificationLevel(models.TextChoices):
    VERIFIED = "verified", "Vérifié"
    SELECTION = "selection", "Sélection Loka"


class ConditionGrade(models.TextChoices):
    BASIC = "basic", "Simple"
    GOOD = "good", "Bon état"
    EXCELLENT = "excellent", "Excellent"


class LocationPrecision(models.TextChoices):
    EXACT = "exact", "Exacte"
    APPROXIMATE = "approximate", "Approximative"


class RentalMode(models.TextChoices):
    NIGHTLY = "nightly", "Nuit"
    MONTHLY = "monthly", "Mois"
    YEARLY = "yearly", "Année"


class Amenity(models.Model):
    class Category(models.TextChoices):
        ESSENTIAL = "essential", "Essentiels"
        COMFORT = "comfort", "Confort"
        BUILDING = "building", "Immeuble"
        SAFETY = "safety", "Sécurité"

    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=80)
    icon = models.CharField(max_length=40, help_text="Nom d'icône lucide côté front")
    category = models.CharField(max_length=16, choices=Category.choices, default=Category.COMFORT)
    order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["category", "order", "name"]
        verbose_name = "équipement"
        verbose_name_plural = "équipements"

    def __str__(self) -> str:
        return self.name


class PropertyQuerySet(models.QuerySet["Property"]):
    def published(self) -> PropertyQuerySet:
        return self.filter(status=PropertyStatus.PUBLISHED)

    def publicly_visible(self) -> PropertyQuerySet:
        """Publié, ou en revue de modifications avec une version publiée à montrer (ADR 0007)."""
        return self.filter(
            models.Q(status=PropertyStatus.PUBLISHED)
            | models.Q(
                status__in=[PropertyStatus.PENDING_REVIEW, PropertyStatus.NEEDS_VISIT],
                published_snapshot__isnull=False,
            )
        )

    def with_public_relations(self) -> PropertyQuerySet:
        return self.select_related(
            "city", "city__governorate", "neighborhood", "host", "host__host_profile"
        ).prefetch_related("photos", "pricing_plans", "amenities")

    def for_public(self) -> PropertyQuerySet:
        return self.publicly_visible().with_public_relations()

    def for_public_any_status(self) -> PropertyQuerySet:
        return self.with_public_relations()


class Property(PublicIdModel, TimeStampedModel):
    """Bien mis en location. Le statut ne change que via listings.services (ADR 0003)."""

    TRANSITIONS: ClassVar[dict[str, frozenset[str]]] = {
        PropertyStatus.DRAFT: frozenset({PropertyStatus.PENDING_REVIEW}),
        PropertyStatus.PENDING_REVIEW: frozenset(
            {
                PropertyStatus.NEEDS_VISIT,
                PropertyStatus.PUBLISHED,
                PropertyStatus.REJECTED,
                PropertyStatus.DRAFT,
            }
        ),
        PropertyStatus.NEEDS_VISIT: frozenset(
            {PropertyStatus.PUBLISHED, PropertyStatus.REJECTED, PropertyStatus.PENDING_REVIEW}
        ),
        # ADR 0007 : une modification descriptive d'un bien publié ou en pause le renvoie en revue.
        PropertyStatus.PUBLISHED: frozenset({PropertyStatus.PAUSED, PropertyStatus.PENDING_REVIEW}),
        PropertyStatus.PAUSED: frozenset(
            {PropertyStatus.PUBLISHED, PropertyStatus.DRAFT, PropertyStatus.PENDING_REVIEW}
        ),
        PropertyStatus.REJECTED: frozenset({PropertyStatus.DRAFT}),
    }

    # --- identité
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="properties"
    )
    title = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    description = models.TextField(blank=True)
    property_type = models.CharField(max_length=24, choices=PropertyType.choices)
    rooms_label = models.CharField(max_length=8, blank=True, help_text="S+1, S+2, ...")
    bedrooms = models.PositiveSmallIntegerField(default=0)
    bathrooms = models.PositiveSmallIntegerField(default=1)
    surface_m2 = models.PositiveSmallIntegerField(null=True, blank=True)
    floor = models.SmallIntegerField(null=True, blank=True)
    has_elevator = models.BooleanField(default=False)
    furnished = models.BooleanField(default=True)

    # --- localisation
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="properties")
    neighborhood = models.ForeignKey(
        Neighborhood, on_delete=models.PROTECT, related_name="properties", null=True, blank=True
    )
    # Jamais exposée publiquement. Accès journalisé (ADR 0004).
    address_private = models.CharField(max_length=255, blank=True)
    location = gis_models.PointField(srid=4326, null=True, blank=True)
    location_precision = models.CharField(
        max_length=12, choices=LocationPrecision.choices, default=LocationPrecision.APPROXIMATE
    )

    # --- capacité
    max_guests = models.PositiveSmallIntegerField(default=2)

    # --- statut & vérification
    status = models.CharField(
        max_length=16, choices=PropertyStatus.choices, default=PropertyStatus.DRAFT, db_index=True
    )
    verification_level = models.CharField(
        max_length=12, choices=VerificationLevel.choices, default=VerificationLevel.VERIFIED
    )
    verified_at = models.DateTimeField(null=True, blank=True)
    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="verified_properties",
    )
    verification_notes = models.TextField(blank=True, help_text="Interne, jamais exposé")
    rejection_reason = models.CharField(max_length=255, blank=True)
    visit_scheduled_at = models.DateTimeField(null=True, blank=True)
    condition_grade = models.CharField(
        max_length=12, choices=ConditionGrade.choices, default=ConditionGrade.GOOD
    )

    # --- infos pratiques
    charges_included = models.BooleanField(default=False)
    monthly_charges_estimate = models.DecimalField(
        max_digits=8, decimal_places=0, null=True, blank=True, help_text="TND / mois"
    )
    deposit_months = models.PositiveSmallIntegerField(
        default=1, help_text="Caution en nombre de mois de loyer (mensuel / annuel)"
    )
    min_lease_months = models.PositiveSmallIntegerField(default=1)
    distance_notes = models.JSONField(
        default=dict, blank=True, help_text='{"ESPRIT": "8 min à pied", "Métro Ligne 2": "5 min"}'
    )
    house_rules = models.JSONField(
        default=dict, blank=True, help_text='{"smoking": false, "pets": false, "parties": false}'
    )

    # --- SEO
    meta_title = models.CharField(max_length=120, blank=True)
    meta_description = models.CharField(max_length=320, blank=True)

    published_at = models.DateTimeField(null=True, blank=True)
    rating = models.DecimalField(
        max_digits=2, decimal_places=1, null=True, blank=True, help_text="Note moyenne /5"
    )
    review_count = models.PositiveIntegerField(default=0)
    # ADR 0007 : version publique figée à la publication, servie pendant une revue de modifications.
    published_snapshot = models.JSONField(null=True, blank=True, editable=False)

    amenities: models.ManyToManyField[Amenity, PropertyAmenity] = models.ManyToManyField(
        Amenity, through="PropertyAmenity", blank=True
    )

    objects = PropertyQuerySet.as_manager()

    class Meta:
        verbose_name = "bien"
        ordering = ["-published_at", "-created_at"]
        indexes = [
            models.Index(fields=["city", "status"]),
            models.Index(fields=["neighborhood", "status"]),
        ]

    def __str__(self) -> str:
        return self.title

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)

    def _unique_slug(self) -> str:
        base = slugify(f"{self.title}-{self.city.slug}")[:140] or "bien"
        slug = base
        counter = 2
        while Property.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base}-{counter}"
            counter += 1
        return slug

    @property
    def is_published(self) -> bool:
        return self.status == PropertyStatus.PUBLISHED

    @builtins.property
    def is_serving_snapshot(self) -> bool:
        """En revue de modifications : le public voit l'instantané de la version publiée."""
        return (
            self.status in {PropertyStatus.PENDING_REVIEW, PropertyStatus.NEEDS_VISIT}
            and self.published_snapshot is not None
        )

    @builtins.property
    def is_publicly_visible(self) -> bool:
        return self.is_published or self.is_serving_snapshot

    def mark_published(self) -> None:
        if self.published_at is None:
            self.published_at = timezone.now()


class PropertyAmenity(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    amenity = models.ForeignKey(Amenity, on_delete=models.CASCADE)

    class Meta:
        unique_together = [("property", "amenity")]

    def __str__(self) -> str:
        return f"{self.property_id}:{self.amenity_id}"


def photo_original_upload_to(instance: PropertyPhoto, filename: str) -> str:
    return generated_name(f"photos/{instance.property_id}", filename, forced_ext="jpg")


class PropertyPhoto(PublicIdModel, TimeStampedModel):
    """
    Original stocké dans le bucket privé (jamais servi). Les variantes WebP publiques
    sont générées par notifications.tasks.generate_photo_variants et listées dans `variants`.
    """

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="photos")
    original = models.ImageField(upload_to=photo_original_upload_to, storage=private_storage)
    variants = models.JSONField(default=dict, blank=True, help_text='{"card": "url", ...}')
    width = models.PositiveIntegerField(default=0)
    height = models.PositiveIntegerField(default=0)
    order = models.PositiveSmallIntegerField(default=0)
    is_cover = models.BooleanField(default=False)
    alt_text = models.CharField(max_length=160, blank=True)
    taken_by_team = models.BooleanField(default=False)
    auto_enhance = models.BooleanField(
        default=True,
        verbose_name="retouche automatique",
        help_text=(
            "Retouche automatique des variantes publiques (niveaux, contraste, "
            "balance des blancs). L'original privé n'est jamais modifié."
        ),
    )

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "photo"

    def __str__(self) -> str:
        return f"Photo {self.order} de {self.property_id}"

    # `property` est masqué par le champ FK du même nom : on passe par builtins.
    @builtins.property
    def is_ready(self) -> bool:
        return bool(self.variants)


class PricingPlan(TimeStampedModel):
    """Un plan par mode. Prix en TND : par nuit (nightly), par mois (monthly), par an (yearly)."""

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name="pricing_plans")
    rental_mode = models.CharField(max_length=8, choices=RentalMode.choices)
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(1)],
        help_text="TND par nuit, par mois, ou par an pour le plan annuel (ADR 0007)",
    )
    min_duration = models.PositiveSmallIntegerField(
        default=1, help_text="Nuits (nightly) ou mois (monthly). Ignoré pour yearly (12)."
    )
    max_duration = models.PositiveSmallIntegerField(
        null=True, blank=True, help_text="Nuits ou mois. Vide = pas de maximum."
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("property", "rental_mode")]
        ordering = ["rental_mode"]
        verbose_name = "plan tarifaire"

    def __str__(self) -> str:
        return f"{self.property_id} {self.rental_mode} {self.price} TND"
