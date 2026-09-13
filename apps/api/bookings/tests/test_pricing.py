from datetime import date
from decimal import Decimal

import pytest

from bookings.pricing import PlanData, PricingError, compute_quote, months_between, to_eur

D = Decimal


class TestNightly:
    plan = PlanData("nightly", D("120"), min_duration=2, max_duration=10)

    def test_basic(self):
        q = compute_quote(self.plan, date(2026, 10, 1), date(2026, 10, 4))
        assert q.units == 3
        assert q.unit_label == "nuit"
        assert q.subtotal == D("360.00")
        assert q.fee_rate == D("0.10")
        assert q.fee == D("36.00")
        assert q.fee_payer == "traveler"
        assert q.total == D("396.00")  # frais ajoutés pour le voyageur
        assert q.deposit == D("118.80")  # 30 % du total
        assert q.host_payout == D("360.00")  # l'hôte touche le sous-total complet
        assert q.host_payout_from_deposit == D("118.80")
        assert q.security_deposit == D("0.00")

    def test_rounding_half_up(self):
        q = compute_quote(PlanData("nightly", D("33.33")), date(2026, 10, 1), date(2026, 10, 2))
        assert q.subtotal == D("33.33")
        assert q.fee == D("3.33")
        assert q.total == D("36.66")
        assert q.deposit == D("11.00")

    def test_below_min(self):
        with pytest.raises(PricingError) as exc:
            compute_quote(self.plan, date(2026, 10, 1), date(2026, 10, 2))
        assert exc.value.code == "below_min_duration"

    def test_above_max(self):
        with pytest.raises(PricingError) as exc:
            compute_quote(self.plan, date(2026, 10, 1), date(2026, 10, 20))
        assert exc.value.code == "above_max_duration"

    def test_invalid_dates(self):
        with pytest.raises(PricingError) as exc:
            compute_quote(self.plan, date(2026, 10, 4), date(2026, 10, 1))
        assert exc.value.code == "invalid_dates"
        with pytest.raises(PricingError):
            compute_quote(self.plan, date(2026, 10, 4), date(2026, 10, 4))


class TestMonthly:
    plan = PlanData("monthly", D("850"), min_duration=1, max_duration=11)

    def test_one_month(self):
        q = compute_quote(self.plan, date(2026, 10, 5), date(2026, 11, 5), deposit_months=2)
        assert q.units == 1
        assert q.unit_label == "mois"
        assert q.subtotal == D("850.00")
        assert q.fee_rate == D("0.05")
        assert q.fee == D("42.50")
        assert q.fee_payer == "host"
        assert q.total == D("850.00")  # rien de plus pour le voyageur
        assert q.deposit == D("850.00")  # un mois de loyer
        assert q.host_payout == D("807.50")
        assert q.host_payout_from_deposit == D("807.50")
        assert q.security_deposit == D("1700.00")

    def test_three_months(self):
        q = compute_quote(self.plan, date(2026, 1, 15), date(2026, 4, 15))
        assert q.units == 3
        assert q.subtotal == D("2550.00")
        assert q.fee == D("127.50")
        assert q.host_payout == D("2422.50")
        assert q.deposit == D("850.00")

    def test_partial_months_rejected(self):
        with pytest.raises(PricingError) as exc:
            compute_quote(self.plan, date(2026, 10, 5), date(2026, 11, 20))
        assert exc.value.code == "not_whole_months"

    def test_max_duration(self):
        with pytest.raises(PricingError) as exc:
            compute_quote(self.plan, date(2026, 1, 1), date(2027, 1, 1))
        assert exc.value.code == "above_max_duration"

    def test_min_duration(self):
        plan = PlanData("monthly", D("850"), min_duration=3)
        with pytest.raises(PricingError) as exc:
            compute_quote(plan, date(2026, 1, 1), date(2026, 3, 1))
        assert exc.value.code == "below_min_duration"

    def test_end_of_month_edge(self):
        # 31 janvier -> 28 février : relativedelta borne au dernier jour du mois => 1 mois entier
        q = compute_quote(self.plan, date(2026, 1, 31), date(2026, 2, 28))
        assert q.units == 1


class TestYearly:
    # ADR 0007 : le prix annuel est saisi par l'hôte (ici 8 400 DT pour 12 mois).
    plan = PlanData("yearly", D("8400"))

    def test_twelve_months(self):
        q = compute_quote(self.plan, date(2026, 9, 1), date(2027, 9, 1), deposit_months=1)
        assert q.units == 12
        assert q.unit_label == "an"
        assert q.unit_price == D("8400.00")
        assert q.monthly_equivalent == D("700.00")
        assert q.subtotal == D("8400.00")
        assert q.fee_rate == D("0.03")
        assert q.fee == D("252.00")
        assert q.fee_payer == "host"
        assert q.total == D("8400.00")
        assert q.deposit == D("700.00")  # un douzième
        assert q.host_payout == D("8148.00")
        assert q.host_payout_from_deposit == D("448.00")
        assert q.security_deposit == D("700.00")

    def test_monthly_equivalent_rounding(self):
        q = compute_quote(PlanData("yearly", D("10000")), date(2026, 1, 1), date(2027, 1, 1))
        assert q.monthly_equivalent == D("833.33")
        assert q.deposit == D("833.33")

    def test_not_twelve_months(self):
        with pytest.raises(PricingError) as exc:
            compute_quote(self.plan, date(2026, 9, 1), date(2027, 3, 1))
        assert exc.value.code == "yearly_not_12_months"


class TestHelpers:
    def test_months_between(self):
        assert months_between(date(2026, 1, 15), date(2026, 4, 15)) == 3
        assert months_between(date(2026, 1, 15), date(2027, 1, 15)) == 12
        with pytest.raises(PricingError):
            months_between(date(2026, 1, 15), date(2026, 1, 15))

    def test_unknown_mode(self):
        with pytest.raises(PricingError) as exc:
            compute_quote(PlanData("weekly", D("1")), date(2026, 1, 1), date(2026, 1, 8))
        assert exc.value.code == "unknown_mode"

    def test_to_eur(self):
        assert to_eur(D("1000")) == D("295.00")
