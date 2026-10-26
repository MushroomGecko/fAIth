"""Tests for the login helpers in backend.utils.login."""

from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlencode

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory, TestCase, override_settings

from backend.models import EncryptedTOTPDevice
from backend.utils.authentication import LOCKED_OUT_MESSAGE, TOTP_DEVICE_NAME
from backend.utils.login import (
    INVALID_LOGIN_MESSAGE,
    authenticator_device_id,
    canonical_username,
    get_next_url,
    login_locked,
    login_refused,
    render_login,
)

User = get_user_model()
PASSWORD = "a-long-test-password-123"


async def _acreate_user(username):
    """Create a user from async test code. create_user is synchronous, so it runs in a thread."""
    return await sync_to_async(User.objects.create_user)(username=username, password=PASSWORD)


def _encode(values):
    """Encode a small dict as a query string."""
    return urlencode(values)


@override_settings(LOGIN_REDIRECT_URL="/home/")
class TestGetNextUrl(TestCase):
    """Tests for get_next_url."""

    def _request(self, post=None, query=None, secure=False):
        """Build a request with the given POST and query-string values."""
        factory = RequestFactory()
        path = f"/login/?{_encode(query or {})}"
        if post is not None:
            return factory.post(path, post, secure=secure)
        return factory.get(path, secure=secure)

    async def test_uses_next_from_post(self):
        """A local next value from the login form is used."""
        request = self._request(post={"next": "/books/"})

        assert await get_next_url(request) == "/books/"

    async def test_uses_next_from_query_string_when_post_has_none(self):
        """If the form has no next value, a local next value from the query string is used."""
        request = self._request(query={"next": "/notes/"})

        assert await get_next_url(request) == "/notes/"

    async def test_post_next_wins_over_query_next(self):
        """When both are given, the form value is used."""
        request = self._request(post={"next": "/from-form/"}, query={"next": "/from-query/"})

        assert await get_next_url(request) == "/from-form/"

    async def test_no_next_falls_back_to_login_redirect_url(self):
        """With no next value, the user goes to LOGIN_REDIRECT_URL."""
        request = self._request()

        assert await get_next_url(request) == "/home/"

    async def test_custom_default_is_used_when_next_is_missing(self):
        """A caller-supplied default is used instead of LOGIN_REDIRECT_URL."""
        request = self._request()

        assert await get_next_url(request, default="/custom/") == "/custom/"

    async def test_external_url_is_rejected(self):
        """A next value pointing at another site is never used."""
        request = self._request(post={"next": "https://evil.example.com/steal"})

        assert await get_next_url(request) == "/home/"

    async def test_protocol_relative_url_is_rejected(self):
        """A next value starting with // is treated as an external site and rejected."""
        request = self._request(post={"next": "//evil.example.com/steal"})

        assert await get_next_url(request) == "/home/"

    async def test_javascript_url_is_rejected(self):
        """A javascript: next value is rejected."""
        request = self._request(post={"next": "javascript:alert(1)"})

        assert await get_next_url(request) == "/home/"

    async def test_same_host_absolute_url_is_accepted(self):
        """An absolute URL to this site is allowed."""
        request = self._request(post={"next": "http://testserver/books/"})

        assert await get_next_url(request) == "http://testserver/books/"

    async def test_http_url_is_rejected_on_secure_request(self):
        """On an HTTPS request, a plain http:// next value is rejected."""
        request = self._request(post={"next": "http://testserver/books/"}, secure=True)

        assert await get_next_url(request) == "/home/"

    async def test_empty_next_falls_back_to_default(self):
        """An empty next value is treated the same as a missing one."""
        request = self._request(post={"next": ""})

        assert await get_next_url(request) == "/home/"


class TestCanonicalUsername(TestCase):
    """Tests for canonical_username."""

    def setUp(self):
        self.user = User.objects.create_user(username="StoredName", password=PASSWORD)

    async def test_returns_stored_spelling_for_different_case(self):
        """A username typed in another letter case returns the stored spelling."""
        assert await canonical_username("storedname") == "StoredName"

    async def test_returns_stored_spelling_for_upper_case(self):
        """An all-caps username returns the stored spelling."""
        assert await canonical_username("STOREDNAME") == "StoredName"

    async def test_returns_exact_stored_spelling_unchanged(self):
        """An exact match is returned as is."""
        assert await canonical_username("StoredName") == "StoredName"

    async def test_unknown_username_is_returned_unchanged(self):
        """A username with no matching account is returned exactly as typed."""
        assert await canonical_username("Unknown-Name") == "Unknown-Name"


class TestAuthenticatorDeviceId(TestCase):
    """Tests for authenticator_device_id."""

    async def test_returns_none_without_authenticator(self):
        """A user with no authenticator app has no device ID."""
        user = await _acreate_user("no-totp-user")

        assert await authenticator_device_id(user) is None

    async def test_returns_none_for_unconfirmed_authenticator(self):
        """An unfinished setup can't be used to log in, so it has no device ID."""
        user = await _acreate_user("unconfirmed-totp-user")
        await EncryptedTOTPDevice.objects.acreate(user=user, name=TOTP_DEVICE_NAME, confirmed=False)

        assert await authenticator_device_id(user) is None

    async def test_returns_persistent_id_of_confirmed_device(self):
        """A confirmed authenticator returns its persistent ID, which the login form uses."""
        user = await _acreate_user("confirmed-totp-user")
        device = await EncryptedTOTPDevice.objects.acreate(user=user, name=TOTP_DEVICE_NAME, confirmed=True)

        result = await authenticator_device_id(user)

        assert result == device.persistent_id

    async def test_returns_oldest_confirmed_device_when_several(self):
        """When several confirmed authenticators exist, the oldest one's ID is returned."""
        user = await _acreate_user("several-totp-user")
        first = await EncryptedTOTPDevice.objects.acreate(user=user, name=TOTP_DEVICE_NAME, confirmed=True)
        await EncryptedTOTPDevice.objects.acreate(user=user, name=TOTP_DEVICE_NAME, confirmed=True)

        result = await authenticator_device_id(user)

        assert result == first.persistent_id

    async def test_ignores_other_users_authenticator(self):
        """Another user's authenticator is never returned."""
        user = await _acreate_user("lookup-user")
        other = await _acreate_user("other-totp-owner")
        await EncryptedTOTPDevice.objects.acreate(user=other, name=TOTP_DEVICE_NAME, confirmed=True)

        assert await authenticator_device_id(user) is None


class TestRenderLogin(TestCase):
    """Tests for render_login."""

    async def test_passes_form_and_next_to_template(self):
        """The form and the next value are passed to the login template."""
        form = MagicMock()
        page = HttpResponse("login")
        request = RequestFactory().post("/login/", {"next": "/books/"})

        with patch("backend.utils.login.render_async", new_callable=AsyncMock, return_value=page) as mock_render:
            response = await render_login(request, form, "login.html")

        assert response is page
        args, kwargs = mock_render.call_args
        assert args[1] == "login.html"
        assert args[2] == {"form": form, "next": "/books/"}
        assert kwargs == {"status": 200}

    async def test_next_comes_from_query_string_for_get(self):
        """On a GET request, the next value comes from the query string."""
        request = RequestFactory().get("/login/?next=/notes/")

        with patch(
            "backend.utils.login.render_async", new_callable=AsyncMock, return_value=HttpResponse("")
        ) as mock_render:
            await render_login(request, MagicMock(), "login.html")

        assert mock_render.call_args.args[2]["next"] == "/notes/"

    async def test_next_is_empty_when_missing(self):
        """With no next value anywhere, the context uses an empty string."""
        request = RequestFactory().get("/login/")

        with patch(
            "backend.utils.login.render_async", new_callable=AsyncMock, return_value=HttpResponse("")
        ) as mock_render:
            await render_login(request, MagicMock(), "login.html")

        assert mock_render.call_args.args[2]["next"] == ""

    async def test_passes_custom_status(self):
        """A failed login is rendered with the status the view passes in, such as 400."""
        request = RequestFactory().post("/login/", {})

        with patch(
            "backend.utils.login.render_async", new_callable=AsyncMock, return_value=HttpResponse("")
        ) as mock_render:
            await render_login(request, MagicMock(), "login.html", status=400)

        assert mock_render.call_args.kwargs == {"status": 400}


class TestLoginLocked(TestCase):
    """Tests for login_locked, which shows the lockout message on the login page."""

    async def _render(self):
        """Call login_locked with a mocked renderer and return the page it rendered and the mock."""
        request = RequestFactory().post("/login/", {"username": "lock-user", "password": "wrong"})
        page = HttpResponse("login")

        with patch("backend.utils.login.render_async", new_callable=AsyncMock, return_value=page) as mock_render:
            response = await login_locked(request, "login.html")

        return response, page, mock_render

    async def test_returns_the_rendered_page(self):
        """The response is whatever the renderer produces."""
        response, page, _ = await self._render()

        assert response is page

    async def test_form_carries_the_lockout_message(self):
        """The lockout message is the form's non-field error, so the login template shows it."""
        _, _, mock_render = await self._render()

        form = mock_render.call_args.args[2]["form"]
        assert LOCKED_OUT_MESSAGE in form.non_field_errors()

    async def test_form_is_unbound_so_no_password_is_checked(self):
        """The form isn't bound to the submitted data, so django-otp never validates the password or code."""
        _, _, mock_render = await self._render()

        assert mock_render.call_args.args[2]["form"].is_bound is False

    async def test_uses_given_template_and_status_429(self):
        """The page uses the template the view passes in, with status 429."""
        _, _, mock_render = await self._render()

        assert mock_render.call_args.args[1] == "login.html"
        assert mock_render.call_args.kwargs == {"status": 429}


class TestLoginRefused(TestCase):
    """Tests for login_refused, which shows the generic error for a wrong username or password."""

    async def _refuse(self, username="typed-name"):
        """Call login_refused with a mocked renderer and return the response, the page, and the mock."""
        request = RequestFactory().post("/login/", {"username": username, "password": "wrong"})
        page = HttpResponse("login")

        with patch("backend.utils.login.render_async", new_callable=AsyncMock, return_value=page) as mock_render:
            response = await login_refused(request, "login.html", username)

        return response, page, mock_render

    async def test_returns_the_rendered_page(self):
        """The response is whatever the renderer produces."""
        response, page, _ = await self._refuse()

        assert response is page

    async def test_form_carries_the_generic_login_error(self):
        """The error is Django's generic invalid-login message, so the page doesn't reveal whether the username exists."""
        _, _, mock_render = await self._refuse()

        form = mock_render.call_args.args[2]["form"]
        assert INVALID_LOGIN_MESSAGE in form.non_field_errors()

    async def test_form_is_unbound_so_authenticate_is_not_run_again(self):
        """The form is unbound, so its clean() never calls authenticate(). That call would count the attempt a second time."""
        with patch("django.contrib.auth.forms.authenticate") as mock_authenticate:
            _, _, mock_render = await self._refuse()

        mock_authenticate.assert_not_called()
        assert mock_render.call_args.args[2]["form"].is_bound is False

    async def test_username_is_kept_for_the_user(self):
        """The username the user typed is filled back in, so they don't have to retype it."""
        _, _, mock_render = await self._refuse(username="Typed-Name")

        form = mock_render.call_args.args[2]["form"]
        assert form["username"].value() == "Typed-Name"

    async def test_uses_given_template_and_status_400(self):
        """The page uses the template the view passes in, with status 400."""
        _, _, mock_render = await self._refuse()

        assert mock_render.call_args.args[1] == "login.html"
        assert mock_render.call_args.kwargs == {"status": 400}
