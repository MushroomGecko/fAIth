"""Tests for the signup helpers in backend.utils.signup."""

from base64 import b32encode
from unittest.mock import AsyncMock, MagicMock, patch

from asgiref.sync import sync_to_async
from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.core.exceptions import ValidationError
from django.http import HttpResponse, HttpResponseRedirect
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticDevice

from backend.models import EncryptedTOTPDevice
from backend.utils.authentication import (
    INVALID_CODE_MESSAGE,
    RECOVERY_DEVICE_NAME,
    TOTP_DEVICE_NAME,
)
from backend.utils.hashing import username_hmac
from backend.utils.signup import (
    PENDING_CODES_SESSION_KEY,
    PENDING_DEVICE_SESSION_KEY,
    SignupForm,
    abandon_pending_enrollment,
    clear_pending_device,
    confirm_enrollment,
    create_user_and_devices,
    load_pending_enrollment,
    pending_device,
    read_pending_codes,
    read_pending_device_id,
    render_authenticate,
    skip_enrollment,
    store_pending_device,
)

User = get_user_model()
PASSWORD = "a-long-test-password-123"


def _totp_code(device):
    """Return the 6-digit code the authenticator app would show for this device right now."""
    return str(TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift).token()).zfill(device.digits)


def _signup_data(username):
    """Return valid signup form data for the given username."""
    return {"username": username, "password1": PASSWORD, "password2": PASSWORD}


async def _valid_form(username):
    """Return a bound signup form that has passed validation. is_valid() queries the database, so it runs in a thread."""
    form = SignupForm(data=_signup_data(username))
    assert await sync_to_async(form.is_valid)()
    return form


async def _start_enrollment(username):
    """Create a user with pending devices, store the pending enrollment in a new session, and return them."""
    form = await _valid_form(username)
    totp, codes = await create_user_and_devices(form)
    session = SessionStore()
    await store_pending_device(session, totp.pk, codes)
    return totp, codes, session


def _request_with_session(session, post_data=None):
    """Build a POST request that carries the given session."""
    request = RequestFactory().post("/signup/confirm/", post_data or {})
    request.session = session
    return request


class TestSignupForm(TestCase):
    """Tests for SignupForm.clean_username."""

    def setUp(self):
        self.existing = User.objects.create_user(username="TakenName", password=PASSWORD)

    def test_new_username_is_accepted(self):
        """A username that no account uses is accepted."""
        form = SignupForm(data=_signup_data("brand-new-name"))

        assert form.is_valid()

    def test_exact_duplicate_username_is_rejected(self):
        """A username that exactly matches an existing account is rejected."""
        form = SignupForm(data=_signup_data("TakenName"))

        assert not form.is_valid()
        assert "Username unavailable." in form.errors["username"]

    def test_username_differing_only_in_case_is_rejected(self):
        """A username that differs from an existing one only in letter case is rejected."""
        form = SignupForm(data=_signup_data("takenname"))

        assert not form.is_valid()
        assert "Username unavailable." in form.errors["username"]

    def test_uppercase_variant_is_rejected(self):
        """An all-caps version of an existing username is rejected too."""
        form = SignupForm(data=_signup_data("TAKENNAME"))

        assert not form.is_valid()
        assert "username" in form.errors

    def test_clean_username_keeps_case_of_new_name(self):
        """A valid username is returned exactly as typed, including its letter case."""
        form = SignupForm(data=_signup_data("NewName"))

        assert form.is_valid()
        assert form.cleaned_data["username"] == "NewName"


class TestCreateUserAndDevices(TestCase):
    """Tests for create_user_and_devices."""

    async def test_refuses_name_taken_in_another_letter_case_after_validation(self):
        """A name taken in any letter case after the form was checked is refused, and no second account is saved."""
        form = await _valid_form("lockbob")
        await sync_to_async(User.objects.create_user)(username="LockBob", password=PASSWORD)

        with self.assertRaises(ValidationError):
            await create_user_and_devices(form)

        assert await User.objects.filter(username=username_hmac("lockbob")).acount() == 1

    async def test_saves_user_with_password(self):
        """The user is saved with the chosen password, hashed."""
        form = await _valid_form("signup-create-user")

        await create_user_and_devices(form)

        user = await User.objects.aget(username=username_hmac("signup-create-user"))
        assert user.check_password(PASSWORD)

    async def test_returns_unconfirmed_totp_device(self):
        """The returned authenticator device belongs to the new user and is unconfirmed."""
        form = await _valid_form("signup-totp-user")

        totp, _ = await create_user_and_devices(form)

        assert totp.name == TOTP_DEVICE_NAME
        assert totp.confirmed is False
        assert totp.user.decrypted_username == "signup-totp-user"

    async def test_returns_recovery_codes(self):
        """Ten plain-text recovery codes are returned for the user to save."""
        form = await _valid_form("signup-codes-user")

        _, codes = await create_user_and_devices(form)

        assert len(codes) == 10
        assert all(isinstance(code, str) and code for code in codes)

    async def test_recovery_device_is_saved_confirmed(self):
        """The recovery-code device is confirmed right away, even though the authenticator is not yet confirmed."""
        form = await _valid_form("signup-recovery-user")

        await create_user_and_devices(form)

        device = await StaticDevice.objects.aget(user__username=username_hmac("signup-recovery-user"))
        assert device.name == RECOVERY_DEVICE_NAME
        assert device.confirmed is True

    async def test_totp_device_is_saved_in_database(self):
        """The returned authenticator device is stored, so it can be looked up later."""
        form = await _valid_form("signup-db-user")

        totp, _ = await create_user_and_devices(form)

        assert await EncryptedTOTPDevice.objects.filter(pk=totp.pk, confirmed=False).aexists()


class TestPendingDevice(TestCase):
    """Tests for pending_device."""

    async def test_returns_none_for_missing_id(self):
        """No device ID in the session means there is no pending device."""
        assert await pending_device(None) is None

    async def test_returns_unconfirmed_device(self):
        """An unconfirmed device with this ID is the pending device."""
        totp, _, _ = await _start_enrollment("pending-user")

        found = await pending_device(totp.pk)

        assert found is not None
        assert found.pk == totp.pk

    async def test_returns_none_for_confirmed_device(self):
        """A confirmed device has finished enrollment, so it's no longer pending."""
        totp, _, _ = await _start_enrollment("pending-confirmed-user")
        totp.confirmed = True
        await totp.asave()

        assert await pending_device(totp.pk) is None

    async def test_returns_none_for_unknown_id(self):
        """An ID that doesn't match any device returns None."""
        assert await pending_device(999999) is None


class TestPendingSession(TestCase):
    """Tests for storing, reading, and clearing the pending enrollment in the session."""

    async def test_reads_are_empty_for_new_session(self):
        """A session with no enrollment reports no pending device and no codes."""
        session = SessionStore()

        assert await read_pending_device_id(session) is None
        assert await read_pending_codes(session) == []

    async def test_store_then_read_round_trip(self):
        """What is stored in the session can be read back."""
        session = SessionStore()

        await store_pending_device(session, 42, ["code-one", "code-two"])

        assert await read_pending_device_id(session) == 42
        assert await read_pending_codes(session) == ["code-one", "code-two"]

    async def test_store_uses_expected_session_keys(self):
        """The enrollment is stored under the documented session keys."""
        session = SessionStore()

        code = "3fa2c9d1-07b4e8a5-6c1d0f93-b2e75a48"
        await store_pending_device(session, 7, [code])

        assert await session.aget(PENDING_DEVICE_SESSION_KEY) == 7
        assert code not in await session.aget(PENDING_CODES_SESSION_KEY)
        assert await read_pending_codes(session) == [code]

    async def test_codes_are_unreadable_after_key_change_and_read_as_empty(self):
        """If the encryption key changes, the stored codes can't be decrypted, so they read as empty."""
        session = SessionStore()
        await store_pending_device(session, 9, ["3fa2c9d1-07b4e8a5-6c1d0f93-b2e75a48"])

        with override_settings(RECOVERY_CODE_ENCRYPTION_KEY=Fernet.generate_key().decode()):
            assert await read_pending_codes(session) == []

    async def test_damaged_codes_read_as_empty(self):
        """A stored value that isn't a valid encrypted token reads as empty instead of raising an error."""
        session = SessionStore()
        await session.aset(PENDING_CODES_SESSION_KEY, "not-a-valid-token")

        assert await read_pending_codes(session) == []

    async def test_load_returns_device_and_codes(self):
        """load_pending_enrollment returns the pending device and its codes together."""
        totp, codes, session = await _start_enrollment("load-user")

        device, loaded_codes = await load_pending_enrollment(session)

        assert device is not None
        assert device.pk == totp.pk
        assert loaded_codes == codes

    async def test_load_with_empty_session_returns_none_and_no_codes(self):
        """An empty session loads as no device and no codes."""
        device, codes = await load_pending_enrollment(SessionStore())

        assert device is None
        assert codes == []

    async def test_load_keeps_codes_when_device_is_no_longer_pending(self):
        """If the device has been confirmed, the device is None but the stored codes are still returned."""
        totp, codes, session = await _start_enrollment("load-confirmed-user")
        totp.confirmed = True
        await totp.asave()

        device, loaded_codes = await load_pending_enrollment(session)

        assert device is None
        assert loaded_codes == codes

    async def test_clear_removes_both_keys(self):
        """Clearing the enrollment removes the device ID and the recovery codes."""
        _, _, session = await _start_enrollment("clear-user")

        await clear_pending_device(session)

        assert await read_pending_device_id(session) is None
        assert await read_pending_codes(session) == []

    async def test_clear_on_empty_session_is_harmless(self):
        """Clearing a session with nothing stored doesn't raise an error."""
        session = SessionStore()

        await clear_pending_device(session)

        assert await read_pending_device_id(session) is None


class TestConfirmEnrollment(TestCase):
    """Tests for confirm_enrollment."""

    async def test_without_pending_enrollment_redirects_to_signup(self):
        """With nothing pending, the user is sent back to the start of signup."""
        request = _request_with_session(SessionStore(), {"otp_token": "123456"})

        response = await confirm_enrollment(request, "setup.html")

        assert isinstance(response, HttpResponseRedirect)
        assert response.url == reverse("api:signup")

    async def test_correct_code_confirms_device_and_redirects_to_login(self):
        """A valid code confirms the authenticator and redirects to login."""
        totp, _, session = await _start_enrollment("confirm-ok-user")
        request = _request_with_session(session, {"otp_token": _totp_code(totp)})

        response = await confirm_enrollment(request, "setup.html")

        assert response.url == reverse("api:login")
        await totp.arefresh_from_db()
        assert totp.confirmed is True

    async def test_correct_code_clears_pending_session(self):
        """Once confirmed, the pending enrollment and its recovery codes leave the session."""
        totp, _, session = await _start_enrollment("confirm-clear-user")
        request = _request_with_session(session, {"otp_token": _totp_code(totp)})

        await confirm_enrollment(request, "setup.html")

        assert await read_pending_device_id(session) is None
        assert await read_pending_codes(session) == []

    async def test_code_with_surrounding_spaces_is_accepted(self):
        """A code pasted with extra spaces still confirms the device."""
        totp, _, session = await _start_enrollment("confirm-space-user")
        request = _request_with_session(session, {"otp_token": f"  {_totp_code(totp)} "})

        response = await confirm_enrollment(request, "setup.html")

        assert response.url == reverse("api:login")

    async def test_wrong_code_renders_setup_page_with_error(self):
        """A wrong code shows the setup page again with the invalid-code message and a 400 status."""
        totp, codes, session = await _start_enrollment("confirm-wrong-user")
        request = _request_with_session(session, {"otp_token": "000000"})
        page = HttpResponse("setup", status=400)

        with patch("backend.utils.signup.render_async", new_callable=AsyncMock, return_value=page) as mock_render:
            response = await confirm_enrollment(request, "setup.html")

        assert response is page
        args, kwargs = mock_render.call_args
        assert args[1] == "setup.html"
        assert args[2]["error"] == INVALID_CODE_MESSAGE
        assert args[2]["codes"] == codes
        assert kwargs == {"status": 400}

    async def test_wrong_code_keeps_device_unconfirmed(self):
        """A wrong code leaves the authenticator unconfirmed."""
        totp, _, session = await _start_enrollment("confirm-keep-user")
        request = _request_with_session(session, {"otp_token": "000000"})

        with patch("backend.utils.signup.render_async", new_callable=AsyncMock, return_value=HttpResponse("")):
            await confirm_enrollment(request, "setup.html")

        await totp.arefresh_from_db()
        assert totp.confirmed is False

    async def test_wrong_code_keeps_pending_session(self):
        """A wrong code leaves the pending enrollment in the session so the user can try again."""
        totp, codes, session = await _start_enrollment("confirm-retry-user")
        request = _request_with_session(session, {"otp_token": "000000"})

        with patch("backend.utils.signup.render_async", new_callable=AsyncMock, return_value=HttpResponse("")):
            await confirm_enrollment(request, "setup.html")

        assert await read_pending_device_id(session) == totp.pk
        assert await read_pending_codes(session) == codes


class TestSkipEnrollment(TestCase):
    """Tests for skip_enrollment."""

    async def test_without_pending_enrollment_redirects_to_signup(self):
        """With nothing pending, skipping sends the user back to the start of signup."""
        request = _request_with_session(SessionStore())

        response = await skip_enrollment(request)

        assert response.url == reverse("api:signup")

    async def test_deletes_unconfirmed_authenticator_device(self):
        """Skipping removes the unfinished authenticator setup, so the account has no TOTP."""
        totp, _, session = await _start_enrollment("skip-totp-user")
        request = _request_with_session(session)

        await skip_enrollment(request)

        assert not await EncryptedTOTPDevice.objects.filter(pk=totp.pk).aexists()

    async def test_keeps_recovery_codes(self):
        """Skipping keeps the recovery codes on the account."""
        totp, _, session = await _start_enrollment("skip-recovery-user")
        request = _request_with_session(session)

        await skip_enrollment(request)

        assert await StaticDevice.objects.filter(user=totp.user, name=RECOVERY_DEVICE_NAME).aexists()

    async def test_skipped_recovery_codes_are_confirmed(self):
        """Skipping only removes the authenticator. The recovery codes stay confirmed so they can be used."""
        totp, _, session = await _start_enrollment("skip-confirmed-codes-user")
        request = _request_with_session(session)

        await skip_enrollment(request)

        device = await StaticDevice.objects.aget(user=totp.user, name=RECOVERY_DEVICE_NAME)
        assert device.confirmed is True

    async def test_keeps_confirmed_authenticator_device(self):
        """A confirmed authenticator on the same account is not deleted by skipping."""
        totp, _, session = await _start_enrollment("skip-confirmed-user")
        confirmed = await EncryptedTOTPDevice.objects.acreate(user=totp.user, name=TOTP_DEVICE_NAME, confirmed=True)
        request = _request_with_session(session)

        await skip_enrollment(request)

        assert await EncryptedTOTPDevice.objects.filter(pk=confirmed.pk).aexists()

    async def test_clears_pending_session(self):
        """Skipping forgets the pending enrollment and its recovery codes."""
        _, _, session = await _start_enrollment("skip-session-user")
        request = _request_with_session(session)

        await skip_enrollment(request)

        assert await read_pending_device_id(session) is None
        assert await read_pending_codes(session) == []

    async def test_redirects_to_login(self):
        """A successful skip redirects to login."""
        _, _, session = await _start_enrollment("skip-redirect-user")
        request = _request_with_session(session)

        response = await skip_enrollment(request)

        assert isinstance(response, HttpResponseRedirect)
        assert response.url == reverse("api:login")


class TestAbandonPendingEnrollment(TestCase):
    """Tests for abandon_pending_enrollment."""

    async def test_deletes_unconfirmed_authenticator_device(self):
        """Abandoning removes the unfinished authenticator setup."""
        totp, _, session = await _start_enrollment("abandon-user")

        await abandon_pending_enrollment(session)

        assert not await EncryptedTOTPDevice.objects.filter(pk=totp.pk).aexists()

    async def test_keeps_recovery_codes(self):
        """Abandoning keeps the recovery codes on the account."""
        totp, _, session = await _start_enrollment("abandon-recovery-user")

        await abandon_pending_enrollment(session)

        assert await StaticDevice.objects.filter(user=totp.user, name=RECOVERY_DEVICE_NAME).aexists()

    async def test_clears_pending_session(self):
        """Abandoning forgets the pending enrollment."""
        _, _, session = await _start_enrollment("abandon-session-user")

        await abandon_pending_enrollment(session)

        assert await read_pending_device_id(session) is None
        assert await read_pending_codes(session) == []

    async def test_without_pending_enrollment_does_nothing(self):
        """With nothing pending, abandoning doesn't raise an error."""
        await abandon_pending_enrollment(SessionStore())


class TestRenderAuthenticate(TestCase):
    """Tests for render_authenticate."""

    async def _device(self, username):
        """Create an unconfirmed authenticator device for a new user."""
        form = await _valid_form(username)
        totp, _ = await create_user_and_devices(form)
        return totp

    async def test_context_includes_qr_secret_and_codes(self):
        """The page gets the inline SVG, the manual secret, and the recovery codes."""
        totp = await self._device("render-user")
        codes = ["code-a", "code-b"]
        page = HttpResponse("setup")

        with patch("backend.utils.signup.render_async", new_callable=AsyncMock, return_value=page) as mock_render:
            response = await render_authenticate(MagicMock(), totp, codes, "setup.html")

        assert response is page
        context = mock_render.call_args.args[2]
        assert "<svg" in context["svg"]
        assert context["secret"] == b32encode(totp.bin_key).decode()
        assert context["codes"] == codes
        assert context["error"] is None

    async def test_default_status_is_200(self):
        """If no status is given, the page is rendered with 200."""
        totp = await self._device("render-default-user")

        with patch(
            "backend.utils.signup.render_async", new_callable=AsyncMock, return_value=HttpResponse("")
        ) as mock_render:
            await render_authenticate(MagicMock(), totp, [], "setup.html")

        assert mock_render.call_args.kwargs == {"status": 200}

    async def test_passes_status_and_error_through(self):
        """A custom status and error message are passed to the page."""
        totp = await self._device("render-error-user")

        with patch(
            "backend.utils.signup.render_async", new_callable=AsyncMock, return_value=HttpResponse("")
        ) as mock_render:
            await render_authenticate(MagicMock(), totp, [], "setup.html", status=400, error="Nope")

        context = mock_render.call_args.args[2]
        assert context["error"] == "Nope"
        assert mock_render.call_args.kwargs == {"status": 400}

    async def test_codes_none_is_passed_through(self):
        """When the codes are no longer shown, None is passed to the page."""
        totp = await self._device("render-none-user")

        with patch(
            "backend.utils.signup.render_async", new_callable=AsyncMock, return_value=HttpResponse("")
        ) as mock_render:
            await render_authenticate(MagicMock(), totp, None, "setup.html")

        assert mock_render.call_args.args[2]["codes"] is None
