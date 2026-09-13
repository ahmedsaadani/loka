import json
from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings

from listings import services
from listings.factories import make_published_property
from notifications.tasks import revalidate_front

pytestmark = pytest.mark.django_db


class TestRevalidateTask:
    def test_disabled_without_settings(self):
        with override_settings(REVALIDATE_URL="", REVALIDATE_SECRET=""):
            assert revalidate_front(["/"]) is False

    def test_posts_paths_with_secret(self):
        response = MagicMock()
        response.status = 200
        response.__enter__.return_value = response
        with (
            override_settings(
                REVALIDATE_URL="http://web:3000/api/revalidate", REVALIDATE_SECRET="s3cret"
            ),
            patch("urllib.request.urlopen", return_value=response) as urlopen,
        ):
            assert revalidate_front(["/", "/logement/x"], ["property:x"]) is True
        request = urlopen.call_args.args[0]
        assert request.full_url == "http://web:3000/api/revalidate"
        assert request.get_header("X-revalidate-secret") == "s3cret"
        assert json.loads(request.data) == {"paths": ["/", "/logement/x"], "tags": ["property:x"]}


class TestServicesTriggerRevalidation:
    def test_pause_and_resume_revalidate_pages(self, staff):
        prop = make_published_property()
        with patch("notifications.tasks.revalidate_front.delay") as delay:
            services.pause(prop, by=staff)
            services.resume(prop, by=staff)
        assert delay.call_count == 2
        paths = delay.call_args.args[0]
        assert f"/logement/{prop.slug}" in paths
        assert f"/location/{prop.city.slug}" in paths
        assert f"/location/{prop.city.slug}/{prop.neighborhood.slug}" in paths

    def test_pricing_change_revalidates_only_published(self, staff):
        published = make_published_property()
        draft = make_published_property(status="draft")
        with patch("notifications.tasks.revalidate_front.delay") as delay:
            services.upsert_pricing_plan(published, rental_mode="monthly", price="900")
            services.upsert_pricing_plan(draft, rental_mode="monthly", price="900")
        assert delay.call_count == 1
