"""End-to-end checks that csrf_protect is enforced on real requests through the test client."""

from django.test import Client, TestCase
from django.urls import reverse


class TestAccountRouteCsrf(TestCase):
    """A POST to an account route needs the token from the page that rendered the form."""

    def test_post_without_token_is_forbidden(self):
        client = Client(enforce_csrf_checks=True)

        response = client.post(reverse("api:recover"), {"username": "nobody"})

        assert response.status_code == 403

    def test_post_with_token_is_accepted(self):
        client = Client(enforce_csrf_checks=True)
        client.get(reverse("api:recover"))
        token = client.cookies["csrftoken"].value

        response = client.post(reverse("api:recover"), {"username": "nobody", "csrfmiddlewaretoken": token})

        assert response.status_code != 403


class TestAiRouteCsrf(TestCase):
    """A POST to an AI route is refused without a token, even with a valid payload."""

    def test_post_without_token_is_forbidden(self):
        client = Client(enforce_csrf_checks=True)

        response = client.post(reverse("api:search"), {"collection_name": "x", "query": "hello"})

        assert response.status_code == 403
