import pytest
from django.urls import reverse

from core.checks import PLACEHOLDER
from core.content import pending_entries, public_text
from core.markdown import render_markdown
from core.models import SiteContent
from geo.factories import CityFactory, NeighborhoodFactory

pytestmark = pytest.mark.django_db

LIST_URL = reverse("admin-content-to-write")
PREVIEW_URL = reverse("admin-content-preview")


class TestMarkdown:
    def test_mirrors_front_subset(self):
        html = render_markdown(
            "# Titre\n\nUn **gras** et un [lien](https://loka.tn).\n- a\n- b\n\n### Sous\ntexte"
        )
        assert html == (
            "<h2>Titre</h2>\n<p>Un <strong>gras</strong> et un "
            '<a href="https://loka.tn" rel="noopener">lien</a>.</p>\n'
            "<ul><li>a</li><li>b</li></ul>\n<h3>Sous</h3>\n<p>texte</p>"
        )

    def test_html_is_escaped_and_unsafe_links_ignored(self):
        html = render_markdown("<script>x</script> [x](javascript:alert(1))")
        assert "<script>" not in html
        assert "javascript:" not in html or "href" not in html
        assert "&lt;script&gt;" in html

    def test_public_text_masks_placeholder(self):
        assert public_text(f"{PLACEHOLDER} bientôt") == ""
        assert public_text("Rédigé") == "Rédigé"
        assert public_text("") == ""


class TestInventory:
    def test_lists_cities_neighborhoods_and_pages(self):
        city = CityFactory(intro_text=f"{PLACEHOLDER} ville", seo_title="Titre ok")
        NeighborhoodFactory(city=city, intro_text="Rédigé", seo_description=f"{PLACEHOLDER} q")
        SiteContent.objects.create(key="cgu", title="CGU", body=f"## CGU\n\n{PLACEHOLDER} corps")
        keys = [(e.kind, e.field) for e in pending_entries()]
        assert keys == [
            ("page", "body"),
            ("city", "intro_text"),
            ("neighborhood", "seo_description"),
        ]


class TestAdminScreen:
    def test_requires_staff(self, client):
        response = client.get(LIST_URL)
        assert response.status_code == 302
        assert "/admin/login/" in response["Location"]

    def test_list_and_editor(self, client, admin):
        city = CityFactory(name="Ariana", intro_text=f"{PLACEHOLDER} ville")
        client.force_login(admin)
        response = client.get(LIST_URL)
        assert response.status_code == 200
        assert "Ville « Ariana »" in response.content.decode()
        response = client.get(LIST_URL, {"key": f"city:{city.pk}:intro_text"})
        body = response.content.decode()
        assert "ctw-value" in body
        assert "Markdown supporté" in body

    def test_save_publishes_text(self, client, admin):
        city = CityFactory(intro_text=f"{PLACEHOLDER} ville")
        client.force_login(admin)
        response = client.post(
            LIST_URL, {"key": f"city:{city.pk}:intro_text", "value": "## Ariana\n\nRédigé."}
        )
        assert response.status_code == 302
        city.refresh_from_db()
        assert city.intro_text == "## Ariana\n\nRédigé."
        assert pending_entries() == []

    def test_save_rejects_empty_and_unknown(self, client, admin):
        city = CityFactory(intro_text=f"{PLACEHOLDER} ville")
        client.force_login(admin)
        assert (
            client.post(LIST_URL, {"key": "city:999999:intro_text", "value": "x"}).status_code
            == 400
        )
        client.post(LIST_URL, {"key": f"city:{city.pk}:intro_text", "value": "   "})
        city.refresh_from_db()
        assert PLACEHOLDER in city.intro_text

    def test_preview_endpoint(self, client, admin):
        client.force_login(admin)
        response = client.post(PREVIEW_URL, {"value": f"**gras** {PLACEHOLDER}"})
        assert response.status_code == 200
        assert response.json() == {
            "html": f"<p><strong>gras</strong> {PLACEHOLDER}</p>",
            "pending": True,
        }

    def test_index_shows_pending_count(self, client, admin):
        CityFactory(intro_text=f"{PLACEHOLDER} ville")
        client.force_login(admin)
        response = client.get(reverse("admin:index"))
        assert "Contenus à rédiger" in response.content.decode()


class TestPublicMasking:
    def test_city_detail_hides_placeholder_texts(self, api):
        city = CityFactory(
            intro_text=f"{PLACEHOLDER} ville",
            seo_title="Titre ok",
            seo_description=f"{PLACEHOLDER} d",
        )
        data = api.get(reverse("v1:city-detail", kwargs={"slug": city.slug})).json()
        assert data["intro_text"] == ""
        assert data["seo_title"] == "Titre ok"
        assert data["seo_description"] == ""

    def test_neighborhood_detail_hides_placeholder_texts(self, api):
        hood = NeighborhoodFactory(intro_text=f"{PLACEHOLDER} quartier")
        url = reverse(
            "v1:neighborhood-detail", kwargs={"city_slug": hood.city.slug, "slug": hood.slug}
        )
        assert api.get(url).json()["intro_text"] == ""

    def test_site_content_hides_placeholder_body(self, api):
        SiteContent.objects.create(key="cgu", title="CGU", body=f"## CGU\n\n{PLACEHOLDER} corps")
        data = api.get(reverse("v1:site-content", kwargs={"key": "cgu"})).json()
        assert data["body"] == ""
        assert data["needs_writing"] is True
        assert data["title"] == "CGU"
