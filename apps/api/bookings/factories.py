from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

import factory
from django.utils import timezone

from accounts.factories import TravelerFactory
from bookings.models import (
    Booking,
    BookingRequest,
    BookingRequestStatus,
    BookingStatus,
    Payment,
    PaymentKind,
)
from listings.factories import PropertyFactory
from listings.models import RentalMode


class BookingRequestFactory(factory.django.DjangoModelFactory[BookingRequest]):
    class Meta:
        model = BookingRequest

    property = factory.SubFactory(PropertyFactory, published=True)
    traveler = factory.SubFactory(TravelerFactory)
    rental_mode = RentalMode.MONTHLY
    start_date = factory.LazyFunction(lambda: date.today() + timedelta(days=15))
    end_date = factory.LazyAttribute(lambda o: o.start_date + timedelta(days=30))
    guests = 2
    message = "Bonjour, je suis intéressé."
    status = BookingRequestStatus.PENDING
    quoted_units = 1
    quoted_unit_price = Decimal("850.00")
    quoted_subtotal = Decimal("850.00")
    quoted_fee = Decimal("42.50")
    quoted_total = Decimal("850.00")
    quoted_deposit = Decimal("850.00")
    expires_at = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=48))


class BookingFactory(factory.django.DjangoModelFactory[Booking]):
    class Meta:
        model = Booking

    request = factory.SubFactory(BookingRequestFactory, status=BookingRequestStatus.ACCEPTED)
    property = factory.LazyAttribute(lambda o: o.request.property)
    traveler = factory.LazyAttribute(lambda o: o.request.traveler)
    host = factory.LazyAttribute(lambda o: o.request.property.host)
    rental_mode = factory.LazyAttribute(lambda o: o.request.rental_mode)
    start_date = factory.LazyAttribute(lambda o: o.request.start_date)
    end_date = factory.LazyAttribute(lambda o: o.request.end_date)
    total_amount = factory.LazyAttribute(lambda o: o.request.quoted_total)
    deposit_amount = factory.LazyAttribute(lambda o: o.request.quoted_deposit)
    platform_fee = factory.LazyAttribute(lambda o: o.request.quoted_fee)
    fee_payer = "host"
    status = BookingStatus.AWAITING_DEPOSIT


class PaymentFactory(factory.django.DjangoModelFactory[Payment]):
    class Meta:
        model = Payment

    booking = factory.SubFactory(BookingFactory)
    provider = "mock"
    provider_ref = factory.Sequence(lambda n: f"mock_ref_{n}")
    amount = factory.LazyAttribute(lambda o: o.booking.deposit_amount)
    kind = PaymentKind.DEPOSIT
