from datetime import date, timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from availability import services
from availability.factories import AvailabilityBlockFactory, ExternalCalendarFactory
from availability.models import AvailabilityBlock, BlockKind
from bookings.factories import BookingFactory
from core.exceptions import ConflictError
from listings.factories import PropertyFactory

pytestmark = pytest.mark.django_db

TODAY = date.today()
D = lambda n: TODAY + timedelta(days=n)  # noqa: E731


class TestOverlap:
    @pytest.mark.parametrize(
        ("start", "end", "expected"),
        [
            (10, 13, True),  # identique
            (8, 11, True),  # chevauche le début
            (12, 15, True),  # chevauche la fin
            (11, 12, True),  # inclus
            (5, 20, True),  # englobe
            (7, 10, False),  # se termine le jour de début : autorisé [start, end)
            (13, 16, False),  # commence le jour de fin : autorisé
            (1, 5, False),
        ],
    )
    def test_boundaries(self, start, end, expected):
        prop = PropertyFactory()
        AvailabilityBlockFactory(property=prop, start=D(10), end=D(13))
        assert services.is_available(prop, D(start), D(end)) is (not expected)

    def test_other_property_does_not_block(self):
        prop = PropertyFactory()
        AvailabilityBlockFactory(start=D(10), end=D(13))  # autre bien
        assert services.is_available(prop, D(10), D(13))

    def test_invalid_range_not_available(self):
        prop = PropertyFactory()
        assert services.is_available(prop, D(5), D(5)) is False
        assert services.is_available(prop, D(6), D(5)) is False

    def test_assert_available_past_dates(self):
        prop = PropertyFactory()
        with pytest.raises(ValidationError):
            services.assert_available(prop, D(-1), D(2))

    def test_assert_available_conflict(self):
        prop = PropertyFactory()
        AvailabilityBlockFactory(
            property=prop, start=D(10), end=D(13), kind=BlockKind.EXTERNAL_ICAL
        )
        with pytest.raises(ConflictError):
            services.assert_available(prop, D(11), D(12))


class TestDbConstraint:
    def test_two_booked_blocks_cannot_overlap(self):
        booking = BookingFactory()
        prop = booking.property
        AvailabilityBlock.objects.create(
            property=prop, start=D(10), end=D(13), kind=BlockKind.BOOKED, booking=booking
        )
        other = BookingFactory(request__property=prop)
        with pytest.raises(IntegrityError), transaction.atomic():
            AvailabilityBlock.objects.create(
                property=prop, start=D(12), end=D(14), kind=BlockKind.BOOKED, booking=other
            )

    def test_adjacent_booked_blocks_allowed(self):
        booking = BookingFactory()
        prop = booking.property
        AvailabilityBlock.objects.create(
            property=prop, start=D(10), end=D(13), kind=BlockKind.BOOKED, booking=booking
        )
        other = BookingFactory(request__property=prop)
        AvailabilityBlock.objects.create(
            property=prop, start=D(13), end=D(15), kind=BlockKind.BOOKED, booking=other
        )

    def test_host_blocks_may_overlap_each_other(self):
        prop = PropertyFactory()
        AvailabilityBlockFactory(property=prop, start=D(10), end=D(13))
        AvailabilityBlockFactory(property=prop, start=D(11), end=D(14))

    def test_end_before_start_rejected(self):
        with pytest.raises(IntegrityError), transaction.atomic():
            AvailabilityBlockFactory(start=D(10), end=D(10))


class TestHostBlocks:
    def test_block_and_unblock(self):
        prop = PropertyFactory()
        block = services.block_dates(prop, D(10), D(13), note="travaux")
        assert block.kind == BlockKind.BLOCKED_BY_HOST
        services.unblock(block)
        assert AvailabilityBlock.objects.count() == 0

    def test_block_over_booking_refused(self):
        booking = BookingFactory()
        services.book_period(booking)
        with pytest.raises(ConflictError):
            services.block_dates(booking.property, booking.start_date, booking.end_date)

    def test_cannot_unblock_booking(self):
        booking = BookingFactory()
        block = services.book_period(booking)
        with pytest.raises(ConflictError):
            services.unblock(block)

    def test_book_period_then_release(self):
        booking = BookingFactory()
        services.book_period(booking)
        assert not services.is_available(booking.property, booking.start_date, booking.end_date)
        assert services.release_booking(booking) == 1
        assert services.is_available(booking.property, booking.start_date, booking.end_date)

    def test_book_period_conflict(self):
        booking = BookingFactory()
        AvailabilityBlockFactory(
            property=booking.property, start=booking.start_date, end=booking.end_date
        )
        with pytest.raises(ConflictError):
            services.book_period(booking)


class TestUnavailableRanges:
    def test_merges_and_clips(self):
        prop = PropertyFactory()
        AvailabilityBlockFactory(property=prop, start=D(1), end=D(4))
        AvailabilityBlockFactory(property=prop, start=D(3), end=D(6))
        AvailabilityBlockFactory(property=prop, start=D(10), end=D(30))
        ranges = services.unavailable_ranges(prop, D(2), D(12))
        assert ranges == [(D(2), D(6)), (D(10), D(12))]


ICAL = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Airbnb Inc//Hosting Calendar 0.8.8//EN
BEGIN:VEVENT
DTSTAMP:20260901T000000Z
DTSTART;VALUE=DATE:{s1}
DTEND;VALUE=DATE:{e1}
UID:abc123@airbnb.com
SUMMARY:Reserved
END:VEVENT
BEGIN:VEVENT
DTSTART:{s2}T140000Z
DTEND:{e2}T110000Z
UID:def456@airbnb.com
END:VEVENT
BEGIN:VEVENT
DTSTART;VALUE=DATE:20200101
DTEND;VALUE=DATE:20200105
UID:old@airbnb.com
END:VEVENT
END:VCALENDAR
"""


def ical_text():
    fmt = lambda d: d.strftime("%Y%m%d")  # noqa: E731
    return ICAL.format(s1=fmt(D(20)), e1=fmt(D(23)), s2=fmt(D(30)), e2=fmt(D(32)))


class TestIcal:
    def test_parse(self):
        events = services.parse_ical_events(ical_text())
        assert len(events) == 3
        assert events[0] == ("abc123@airbnb.com", D(20), D(23))
        assert events[1] == ("def456@airbnb.com", D(30), D(32))

    def test_apply_creates_blocks_and_skips_past(self):
        calendar = ExternalCalendarFactory()
        created = services.apply_ical_events(calendar, services.parse_ical_events(ical_text()))
        assert created == 2
        blocks = AvailabilityBlock.objects.filter(external_calendar=calendar)
        assert blocks.count() == 2
        assert all(b.kind == BlockKind.EXTERNAL_ICAL for b in blocks)
        assert calendar.last_synced_at is not None

    def test_apply_is_idempotent(self):
        calendar = ExternalCalendarFactory()
        events = services.parse_ical_events(ical_text())
        services.apply_ical_events(calendar, events)
        services.apply_ical_events(calendar, events)
        assert AvailabilityBlock.objects.filter(external_calendar=calendar).count() == 2

    def test_apply_skips_events_overlapping_bookings(self):
        booking = BookingFactory(request__start_date=D(20), request__end_date=D(22))
        services.book_period(booking)
        calendar = ExternalCalendarFactory(property=booking.property)
        created = services.apply_ical_events(calendar, services.parse_ical_events(ical_text()))
        assert created == 1
        assert not AvailabilityBlock.objects.filter(
            external_calendar=calendar, start=D(20)
        ).exists()
