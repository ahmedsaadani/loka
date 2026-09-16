import pytest
from django.urls import reverse

from accounts.factories import HostFactory, TravelerFactory
from listings.factories import make_published_property
from messaging.models import Conversation, Message

pytestmark = pytest.mark.django_db

LIST = reverse("v1:conversation-list")
UNREAD = reverse("v1:unread-list")


def detail(conv):
    return reverse("v1:conversation-detail", kwargs={"public_id": conv.public_id})


def messages_url(conv):
    return reverse("v1:conversation-messages", kwargs={"public_id": conv.public_id})


class TestStart:
    def test_unauthenticated(self, api):
        assert api.post(LIST, {"property": "x", "body": "hi"}).status_code == 401

    def test_traveler_starts_and_host_gets_unread(self, as_user, host, traveler):
        prop = make_published_property(host=host)
        client = as_user(traveler)
        res = client.post(LIST, {"property": prop.slug, "body": "Bonjour, dispo en août ?"})
        assert res.status_code == 201, res.data
        conv = Conversation.objects.get()
        assert conv.traveler_id == traveler.id and conv.host_id == host.id
        assert conv.messages.count() == 1
        # L'hôte a un message non lu.
        host_unread = as_user(host).get(UNREAD).json()["count"]
        assert host_unread == 1
        # L'auteur, non.
        assert client.get(UNREAD).json()["count"] == 0

    def test_second_message_reuses_conversation(self, as_user, host, traveler):
        prop = make_published_property(host=host)
        client = as_user(traveler)
        client.post(LIST, {"property": prop.slug, "body": "un"})
        client.post(LIST, {"property": prop.slug, "body": "deux"})
        assert Conversation.objects.count() == 1
        assert Message.objects.count() == 2

    def test_host_cannot_message_own_property(self, as_user, host):
        prop = make_published_property(host=host)
        res = as_user(host).post(LIST, {"property": prop.slug, "body": "hi"})
        assert res.status_code == 400

    def test_unknown_property(self, as_user, traveler):
        assert as_user(traveler).post(LIST, {"property": "nope", "body": "hi"}).status_code == 404


class TestThread:
    def _conv(self, as_user, host, traveler):
        prop = make_published_property(host=host)
        as_user(traveler).post(LIST, {"property": prop.slug, "body": "Bonjour"})
        return Conversation.objects.get()

    def test_reply_and_read_flow(self, as_user, host, traveler):
        conv = self._conv(as_user, host, traveler)
        # L'hôte répond.
        res = as_user(host).post(messages_url(conv), {"body": "Oui, c'est libre."})
        assert res.status_code == 201
        # Le voyageur a 1 non-lu, puis ouvre la conversation → lu.
        assert as_user(traveler).get(UNREAD).json()["count"] == 1
        opened = as_user(traveler).get(detail(conv))
        assert opened.status_code == 200
        assert len(opened.json()["messages"]) == 2
        assert as_user(traveler).get(UNREAD).json()["count"] == 0

    def test_list_only_shows_participant_conversations(self, as_user, host, traveler):
        conv = self._conv(as_user, host, traveler)
        assert len(as_user(traveler).get(LIST).json()["results"]) == 1
        assert len(as_user(host).get(LIST).json()["results"]) == 1
        stranger = TravelerFactory()
        assert as_user(stranger).get(LIST).json()["results"] == []
        assert as_user(stranger).get(detail(conv)).status_code == 404

    def test_stranger_cannot_post(self, as_user, host, traveler):
        conv = self._conv(as_user, host, traveler)
        stranger = HostFactory()
        assert as_user(stranger).post(messages_url(conv), {"body": "x"}).status_code == 404
