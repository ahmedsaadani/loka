from __future__ import annotations

from datetime import date, timedelta

import factory

from availability.models import AvailabilityBlock, BlockKind, CalendarSource, ExternalCalendar
from listings.factories import PropertyFactory


class AvailabilityBlockFactory(factory.django.DjangoModelFactory[AvailabilityBlock]):
    class Meta:
        model = AvailabilityBlock

    property = factory.SubFactory(PropertyFactory)
    start = factory.LazyFunction(lambda: date.today() + timedelta(days=10))
    end = factory.LazyAttribute(lambda o: o.start + timedelta(days=3))
    kind = BlockKind.BLOCKED_BY_HOST


class ExternalCalendarFactory(factory.django.DjangoModelFactory[ExternalCalendar]):
    class Meta:
        model = ExternalCalendar

    property = factory.SubFactory(PropertyFactory)
    ical_url = factory.Sequence(lambda n: f"https://calendar.test/{n}.ics")
    source = CalendarSource.AIRBNB
