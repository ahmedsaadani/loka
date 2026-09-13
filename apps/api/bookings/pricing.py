"""
Calcul de devis. Pur (sans accès base) pour être testé exhaustivement.

Règles (ADR 0003, ADR 0007) :
- nightly : prix × nuits ; frais 10 % à la charge du voyageur, ajoutés au total ;
  acompte = 30 % du total voyageur.
- monthly : loyer × mois ; frais 5 % à la charge de l'hôte, déduits de l'acompte ;
  acompte = 1 mois de loyer.
- yearly : prix annuel saisi par l'hôte (12 mois exactement) ; frais 3 % à la charge de l'hôte ;
  acompte = un douzième du prix annuel (un mois). `monthly_equivalent` est indicatif.
Le jour de fin est exclu : [start, end).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from dateutil.relativedelta import relativedelta
from django.conf import settings

TWO_PLACES = Decimal("0.01")
YEARLY_MONTHS = 12


class PricingError(ValueError):
    """Durée ou dates invalides pour ce plan."""

    def __init__(self, message: str, code: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class PlanData:
    rental_mode: str  # nightly | monthly | yearly
    price: Decimal  # TND par nuit (nightly), par mois (monthly) ou par an (yearly)
    min_duration: int = 1
    max_duration: int | None = None


@dataclass(frozen=True)
class Quote:
    rental_mode: str
    units: int  # nuits ou mois
    unit_label: str  # "nuit" | "mois" | "an"
    unit_price: Decimal  # prix par unité affichée (nuit, mois, ou année entière)
    monthly_equivalent: Decimal | None  # yearly uniquement : prix annuel / 12, indicatif
    subtotal: Decimal
    fee_rate: Decimal
    fee: Decimal
    fee_payer: str  # traveler | host
    total: Decimal  # ce que paie le voyageur au total (hors caution)
    deposit: Decimal  # acompte payé sur la plateforme pour confirmer
    host_payout: Decimal  # ce que reçoit l'hôte au total
    host_payout_from_deposit: Decimal  # part de l'acompte reversée à l'hôte
    security_deposit: Decimal  # caution (hors plateforme, informatif)


def money(value: Decimal) -> Decimal:
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def monthly_equivalent(annual_price: Decimal) -> Decimal:
    """Équivalent mensuel indicatif d'un prix annuel."""
    return money(Decimal(annual_price) / YEARLY_MONTHS)


def nights_between(start: date, end: date) -> int:
    return (end - start).days


def months_between(start: date, end: date) -> int:
    """Nombre de mois entiers entre deux dates ; lève PricingError si non entier."""
    delta = relativedelta(end, start)
    if delta.days != 0 or end <= start:
        raise PricingError(
            "Pour une location au mois, la date de fin doit tomber le même jour du mois.",
            code="not_whole_months",
        )
    return delta.years * 12 + delta.months


def compute_quote(
    plan: PlanData,
    start: date,
    end: date,
    *,
    deposit_months: int = 1,
) -> Quote:
    if end <= start:
        raise PricingError("La date de fin doit être après la date de début.", code="invalid_dates")

    mode = plan.rental_mode
    if mode not in settings.PLATFORM_FEE:
        raise PricingError(f"Mode inconnu : {mode}", code="unknown_mode")
    fee_rate: Decimal = settings.PLATFORM_FEE[mode]
    fee_payer: str = settings.PLATFORM_FEE_PAYER[mode]
    price = Decimal(plan.price)
    equivalent: Decimal | None = None

    if mode == "nightly":
        units = nights_between(start, end)
        unit_label = "nuit"
        _check_duration(units, plan)
        subtotal = money(price * units)
        fee = money(subtotal * fee_rate)
        total = money(subtotal + fee)  # frais voyageur ajoutés
        deposit = money(total * settings.BOOKING_DEPOSIT_RATE_NIGHTLY)
        host_payout = subtotal
        host_payout_from_deposit = deposit  # les frais sont dans la part voyageur
        security_deposit = Decimal("0.00")
    elif mode == "monthly":
        units = months_between(start, end)
        unit_label = "mois"
        _check_duration(units, plan)
        subtotal = money(price * units)
        fee = money(subtotal * fee_rate)
        total = subtotal  # frais hôte : rien de plus pour le voyageur
        deposit = money(price)  # 1 mois de loyer
        host_payout = money(subtotal - fee)
        host_payout_from_deposit = money(deposit - fee)
        security_deposit = money(price * deposit_months)
    elif mode == "yearly":
        units = months_between(start, end)
        if units != YEARLY_MONTHS:
            raise PricingError(
                "Une location à l'année dure exactement 12 mois.", code="yearly_not_12_months"
            )
        unit_label = "an"
        equivalent = monthly_equivalent(price)
        subtotal = money(price)  # prix annuel saisi par l'hôte
        fee = money(subtotal * fee_rate)
        total = subtotal
        deposit = equivalent  # un mois
        host_payout = money(subtotal - fee)
        host_payout_from_deposit = money(deposit - fee)
        security_deposit = money(equivalent * deposit_months)
    else:
        raise PricingError(f"Mode inconnu : {mode}", code="unknown_mode")

    return Quote(
        rental_mode=mode,
        units=units,
        unit_label=unit_label,
        unit_price=money(price),
        monthly_equivalent=equivalent,
        subtotal=subtotal,
        fee_rate=fee_rate,
        fee=fee,
        fee_payer=fee_payer,
        total=total,
        deposit=deposit,
        host_payout=host_payout,
        host_payout_from_deposit=host_payout_from_deposit,
        security_deposit=security_deposit,
    )


def _check_duration(units: int, plan: PlanData) -> None:
    if units < max(1, plan.min_duration):
        raise PricingError(f"Durée minimale : {plan.min_duration}.", code="below_min_duration")
    if plan.max_duration is not None and units > plan.max_duration:
        raise PricingError(f"Durée maximale : {plan.max_duration}.", code="above_max_duration")


def to_eur(amount_tnd: Decimal) -> Decimal:
    """Conversion indicative, affichage uniquement."""
    return money(Decimal(amount_tnd) * settings.EUR_RATE)
