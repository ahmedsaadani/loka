from __future__ import annotations

from decimal import Decimal

import factory

from leads.models import Lead, LeadSource, LeadStatus


class LeadFactory(factory.django.DjangoModelFactory[Lead]):
    class Meta:
        model = Lead

    source = LeadSource.TAYARA
    source_url = factory.Sequence(lambda n: f"https://www.tayara.tn/item/{n}")
    title = factory.Sequence(lambda n: f"Appartement S+2 Ariana annonce {n}")
    price = Decimal("900")
    city = "Ariana"
    phone = "+21620000000"
    status = LeadStatus.NEW
