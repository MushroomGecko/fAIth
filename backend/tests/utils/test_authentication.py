"""Tests for the two-factor authentication helpers in backend.utils.authentication."""

import hashlib
import re
from base64 import b32encode, urlsafe_b64encode
from datetime import timedelta
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

from asgiref.sync import async_to_sync, sync_to_async
from axes.exceptions import AxesBackendPermissionDenied
from axes.models import AccessAttempt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.utils import timezone
from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

from backend.models import EncryptedTOTPDevice
from backend.utils.authentication import (
    RECOVERY_CODE_COUNT,
    RECOVERY_CODE_HASH_ITERATIONS,
    RECOVERY_DEVICE_NAME,
    TOTP_DEVICE_NAME,
    AxesLockoutBackend,
    account_locked,
    clear_unconfirmed_totp,
    confirm_device,
    confirmed_recovery_device,
    confirmed_totp_device,
    create_recovery_codes,
    create_totp_device,
    enrollment_details,
    hash_recovery_code,
    record_failed_login,
    render_async,
    unconfirmed_totp_by_device_id,
    unconfirmed_totp_by_user,
    users_matching_username,
    verify_recovery_code,
)

User = get_user_model()
PASSWORD = "a-long-test-password-123"


def _totp_code(device):
    """Return the 6-digit code the authenticator app would show for this device right now."""
    return str(TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift).token()).zfill(device.digits)


async def _acreate_user(username):
    """Create a user from async test code. create_user is synchronous, so it runs in a thread."""
    return await sync_to_async(User.objects.create_user)(username=username, password=PASSWORD)


async def _make_recovery_device_with_code(user, code, confirmed=True):
    """Create a recovery-code device that accepts exactly one code, hashed the way the app hashes it."""
    device = await StaticDevice.objects.acreate(user=user, name=RECOVERY_DEVICE_NAME, confirmed=confirmed)
    await StaticToken.objects.acreate(device=device, token=await hash_recovery_code(code, device))
    return device


class TestHashRecoveryCode(TestCase):
    """Tests for hash_recovery_code."""

    def setUp(self):
        self.user = User.objects.create_user(username="hash-user", password=PASSWORD)
        self.device = StaticDevice.objects.create(user=self.user, name=RECOVERY_DEVICE_NAME, confirmed=True)

    async def test_returns_sixteen_base64url_characters(self):
        """The hash is 96 bits encoded as 16 base64url characters so it fits in StaticToken.token."""
        result = await hash_recovery_code("abcd1234", self.device)

        assert re.fullmatch(r"[A-Za-z0-9_-]{16}", result)

    async def test_matches_pbkdf2_of_normalized_code_and_device_pk(self):
        """The hash is PBKDF2-SHA256 of the lowercase code, salted with the device primary key, first 96 bits."""
        digest = hashlib.pbkdf2_hmac("sha256", b"abcd1234", str(self.device.pk).encode(), RECOVERY_CODE_HASH_ITERATIONS)
        expected = urlsafe_b64encode(digest[:12]).decode("ascii")

        result = await hash_recovery_code("abcd1234", self.device)

        assert result == expected

    async def test_is_case_and_whitespace_insensitive(self):
        """A typed code with different case or surrounding spaces hashes to the same value."""
        plain = await hash_recovery_code("abcd1234", self.device)
        typed = await hash_recovery_code("  ABCD1234 \n", self.device)

        assert typed == plain

    async def test_dashes_and_spaces_are_ignored(self):
        """A code typed with dashes or spaces between groups hashes to the same value as the plain code."""
        plain = await hash_recovery_code("3fa2c9d107b4e8a56c1d0f93b2e75a48", self.device)
        dashed = await hash_recovery_code("3FA2C9D1-07B4E8A5-6C1D0F93-B2E75A48", self.device)
        spaced = await hash_recovery_code("3fa2c9d1 07b4e8a5 6c1d0f93 b2e75a48", self.device)

        assert dashed == plain
        assert spaced == plain

    async def test_is_deterministic(self):
        """Hashing the same code twice gives the same result."""
        first = await hash_recovery_code("abcd1234", self.device)
        second = await hash_recovery_code("abcd1234", self.device)

        assert first == second

    async def test_different_codes_give_different_hashes(self):
        """Two different codes don't hash to the same value."""
        first = await hash_recovery_code("abcd1234", self.device)
        second = await hash_recovery_code("efgh5678", self.device)

        assert first != second

    async def test_same_code_on_different_devices_gives_different_hashes(self):
        """The device primary key is used as salt, so one code hashes differently for each device."""
        other_device = await StaticDevice.objects.acreate(user=self.user, name=RECOVERY_DEVICE_NAME, confirmed=True)

        first = await hash_recovery_code("abcd1234", self.device)
        second = await hash_recovery_code("abcd1234", other_device)

        assert first != second


class TestVerifyRecoveryCode(TestCase):
    """Tests for verify_recovery_code."""

    def setUp(self):
        self.user = User.objects.create_user(username="verify-user", password=PASSWORD)
        self.code = "abcd1234"
        self.device = async_to_sync(_make_recovery_device_with_code)(self.user, self.code)

    async def test_valid_code_returns_true(self):
        """A code that was issued for this device is accepted."""
        assert await verify_recovery_code(self.device, self.code) is True

    async def test_valid_code_is_used_up(self):
        """A successful check deletes the matching token so the code can't be used again."""
        await verify_recovery_code(self.device, self.code)

        assert not await StaticToken.objects.filter(device=self.device).aexists()

    async def test_reused_code_returns_false(self):
        """Once a code has been used, trying it again is refused."""
        await verify_recovery_code(self.device, self.code)

        assert await verify_recovery_code(self.device, self.code) is False

    async def test_typed_code_is_normalized(self):
        """Upper case and surrounding spaces are ignored, so a typed code still matches."""
        assert await verify_recovery_code(self.device, "  ABCD1234  ") is True

    async def test_wrong_code_returns_false_and_keeps_tokens(self):
        """A wrong code is refused and the real token is left in place."""
        assert await verify_recovery_code(self.device, "zzzz9999") is False

        assert await StaticToken.objects.filter(device=self.device).acount() == 1

    async def test_wrong_codes_never_lock_the_device(self):
        """Many wrong codes don't add to the device's throttling count, so they can't lock out the real user."""
        for _ in range(20):
            await verify_recovery_code(self.device, "zzzz9999")

        await self.device.arefresh_from_db()
        assert self.device.throttling_failure_count == 0
        assert await verify_recovery_code(self.device, self.code) is True

    async def test_code_from_another_device_is_refused(self):
        """A code issued to a different user's device doesn't work on this device."""
        other_user = await _acreate_user("other-verify-user")
        other_device = await _make_recovery_device_with_code(other_user, "other123")

        assert await verify_recovery_code(self.device, "other123") is False
        assert await StaticToken.objects.filter(device=other_device).acount() == 1

    async def test_successful_check_records_last_used(self):
        """A valid code sets the device's last-used timestamp."""
        assert self.device.last_used_at is None

        await verify_recovery_code(self.device, self.code)

        await self.device.arefresh_from_db()
        assert self.device.last_used_at is not None

    async def test_leftover_throttle_state_does_not_block_valid_code(self):
        """Old throttling state from before this change can't stop a valid code from working."""
        self.device.throttling_failure_count = 10
        self.device.throttling_failure_timestamp = timezone.now()
        await self.device.asave()

        assert await verify_recovery_code(self.device, self.code) is True


class TestCreateRecoveryCodes(TestCase):
    """Tests for create_recovery_codes."""

    def setUp(self):
        self.user = User.objects.create_user(username="codes-user", password=PASSWORD)

    async def test_returns_expected_number_of_unique_lowercase_codes(self):
        """Creates RECOVERY_CODE_COUNT distinct codes in lowercase."""
        codes = await create_recovery_codes(self.user, confirmed=True)

        assert len(codes) == RECOVERY_CODE_COUNT
        assert len(set(codes)) == RECOVERY_CODE_COUNT
        assert all(isinstance(code, str) and code == code.lower() for code in codes)

    async def test_codes_are_128_bit_hex_in_four_dashed_groups(self):
        """Each code is 32 hex characters (128 bits) shown as four groups of 8, separated by dashes."""
        codes = await create_recovery_codes(self.user, confirmed=True)

        assert all(re.fullmatch(r"[0-9a-f]{8}(-[0-9a-f]{8}){3}", code) for code in codes)

    async def test_creates_recovery_device_for_user(self):
        """Creates one recovery-code device for the user with the expected name."""
        await create_recovery_codes(self.user, confirmed=True)

        device = await StaticDevice.objects.aget(user=self.user)
        assert device.name == RECOVERY_DEVICE_NAME

    async def test_confirmed_flag_is_saved_as_given(self):
        """The device's confirmed flag matches the argument, for both values."""
        other_user = await _acreate_user("codes-user-2")

        await create_recovery_codes(self.user, confirmed=True)
        await create_recovery_codes(other_user, confirmed=False)

        assert (await StaticDevice.objects.aget(user=self.user)).confirmed is True
        assert (await StaticDevice.objects.aget(user=other_user)).confirmed is False

    async def test_stores_only_hashes_not_plaintext(self):
        """The database holds one hash per code and none of the plain-text codes."""
        codes = await create_recovery_codes(self.user, confirmed=True)

        device = await StaticDevice.objects.aget(user=self.user)
        stored = {token.token async for token in StaticToken.objects.filter(device=device)}
        assert len(stored) == RECOVERY_CODE_COUNT
        assert stored.isdisjoint(codes)

    async def test_stored_hashes_match_returned_codes(self):
        """Each stored token is the hash of one of the returned codes."""
        codes = await create_recovery_codes(self.user, confirmed=True)
        device = await StaticDevice.objects.aget(user=self.user)

        stored = {token.token async for token in StaticToken.objects.filter(device=device)}
        expected = {await hash_recovery_code(code, device) for code in codes}
        assert stored == expected

    async def test_every_returned_code_can_be_verified_once(self):
        """Each code returned to the user works exactly one time."""
        codes = await create_recovery_codes(self.user, confirmed=True)
        device = await StaticDevice.objects.aget(user=self.user)

        for code in codes:
            assert await verify_recovery_code(device, code) is True

        # Every code has been used, so a repeat of any of them is refused.
        assert await verify_recovery_code(device, codes[0]) is False


class TestCreateTotpDevice(TestCase):
    """Tests for create_totp_device."""

    def setUp(self):
        self.user = User.objects.create_user(username="totp-create-user", password=PASSWORD)

    async def test_creates_unconfirmed_device_for_user(self):
        """A new authenticator device is created for the user and starts unconfirmed."""
        device = await create_totp_device(self.user)

        assert device.pk is not None
        assert device.user_id == self.user.pk
        assert device.confirmed is False

    async def test_uses_authenticator_device_name(self):
        """The device is named so the login dropdown shows it clearly."""
        device = await create_totp_device(self.user)

        assert device.name == TOTP_DEVICE_NAME
        assert await EncryptedTOTPDevice.objects.filter(pk=device.pk, name=TOTP_DEVICE_NAME).aexists()


class TestConfirmedTotpDevice(TestCase):
    """Tests for confirmed_totp_device."""

    def setUp(self):
        self.user = User.objects.create_user(username="confirmed-totp-user", password=PASSWORD)

    async def test_returns_none_when_user_has_no_devices(self):
        """Returns None if the user has no authenticator device."""
        assert await confirmed_totp_device(self.user) is None

    async def test_ignores_unconfirmed_device(self):
        """An unfinished setup doesn't count as a confirmed device."""
        await create_totp_device(self.user)

        assert await confirmed_totp_device(self.user) is None

    async def test_returns_confirmed_device(self):
        """Returns the user's confirmed device."""
        device = await EncryptedTOTPDevice.objects.acreate(user=self.user, name=TOTP_DEVICE_NAME, confirmed=True)

        found = await confirmed_totp_device(self.user)

        assert found is not None
        assert found.pk == device.pk

    async def test_returns_oldest_when_several_are_confirmed(self):
        """When several confirmed devices exist, the oldest one is returned."""
        first = await EncryptedTOTPDevice.objects.acreate(user=self.user, name=TOTP_DEVICE_NAME, confirmed=True)
        await EncryptedTOTPDevice.objects.acreate(user=self.user, name=TOTP_DEVICE_NAME, confirmed=True)

        found = await confirmed_totp_device(self.user)

        assert found.pk == first.pk

    async def test_ignores_other_users_devices(self):
        """Another user's confirmed device is never returned."""
        other_user = await _acreate_user("someone-else")
        await EncryptedTOTPDevice.objects.acreate(user=other_user, name=TOTP_DEVICE_NAME, confirmed=True)

        assert await confirmed_totp_device(self.user) is None


class TestConfirmedRecoveryDevice(TestCase):
    """Tests for confirmed_recovery_device."""

    def setUp(self):
        self.user = User.objects.create_user(username="confirmed-recovery-user", password=PASSWORD)

    async def test_returns_none_when_user_has_no_devices(self):
        """Returns None if the user has no recovery-code device."""
        assert await confirmed_recovery_device(self.user) is None

    async def test_returns_confirmed_recovery_device(self):
        """Returns the user's confirmed recovery-code device."""
        device = await StaticDevice.objects.acreate(user=self.user, name=RECOVERY_DEVICE_NAME, confirmed=True)

        found = await confirmed_recovery_device(self.user)

        assert found is not None
        assert found.pk == device.pk

    async def test_ignores_unconfirmed_recovery_device(self):
        """Recovery codes that aren't confirmed yet are not returned."""
        await StaticDevice.objects.acreate(user=self.user, name=RECOVERY_DEVICE_NAME, confirmed=False)

        assert await confirmed_recovery_device(self.user) is None

    async def test_ignores_static_devices_with_other_names(self):
        """Only the device named as the recovery code counts."""
        await StaticDevice.objects.acreate(user=self.user, name="Something else", confirmed=True)

        assert await confirmed_recovery_device(self.user) is None


class TestUnconfirmedTotpLookups(TestCase):
    """Tests for unconfirmed_totp_by_user and unconfirmed_totp_by_device_id."""

    def setUp(self):
        self.user = User.objects.create_user(username="unconfirmed-user", password=PASSWORD)
        self.other_user = User.objects.create_user(username="unconfirmed-other", password=PASSWORD)

    async def test_by_user_returns_none_when_no_setup_exists(self):
        """Returns None when the user has no unfinished setup."""
        assert await unconfirmed_totp_by_user(self.user) is None

    async def test_by_user_returns_unconfirmed_device(self):
        """Returns the user's unfinished setup."""
        device = await create_totp_device(self.user)

        found = await unconfirmed_totp_by_user(self.user)

        assert found is not None
        assert found.pk == device.pk

    async def test_by_user_ignores_confirmed_device(self):
        """A confirmed device is not an unfinished setup."""
        await EncryptedTOTPDevice.objects.acreate(user=self.user, name=TOTP_DEVICE_NAME, confirmed=True)

        assert await unconfirmed_totp_by_user(self.user) is None

    async def test_by_user_ignores_other_users_setup(self):
        """Another user's unfinished setup is never returned."""
        await create_totp_device(self.other_user)

        assert await unconfirmed_totp_by_user(self.user) is None

    async def test_by_user_returns_oldest_when_several_exist(self):
        """When several unfinished setups exist, the oldest one is returned."""
        first = await create_totp_device(self.user)
        await create_totp_device(self.user)

        found = await unconfirmed_totp_by_user(self.user)

        assert found.pk == first.pk

    async def test_by_device_id_returns_matching_unconfirmed_device(self):
        """Returns the unfinished setup with this ID."""
        device = await create_totp_device(self.user)

        found = await unconfirmed_totp_by_device_id(device.pk)

        assert found is not None
        assert found.pk == device.pk

    async def test_by_device_id_none_returns_none(self):
        """A missing device ID (no pending signup in the session) returns None."""
        await create_totp_device(self.user)

        assert await unconfirmed_totp_by_device_id(None) is None

    async def test_by_device_id_for_confirmed_device_returns_none(self):
        """A confirmed device can't be fetched as an unfinished setup, even with its ID."""
        device = await EncryptedTOTPDevice.objects.acreate(user=self.user, name=TOTP_DEVICE_NAME, confirmed=True)

        assert await unconfirmed_totp_by_device_id(device.pk) is None

    async def test_by_device_id_for_missing_device_returns_none(self):
        """An ID that doesn't exist returns None."""
        assert await unconfirmed_totp_by_device_id(999999) is None


class TestUsersMatchingUsername(TestCase):
    """Tests for users_matching_username."""

    def setUp(self):
        self.user = User.objects.create_user(username="MixedCase", password=PASSWORD)

    def test_matches_exact_username(self):
        """The exact username matches."""
        assert users_matching_username("MixedCase").exists()

    def test_matches_ignoring_case(self):
        """Usernames match regardless of letter case."""
        assert users_matching_username("mixedcase").exists()
        assert users_matching_username("MIXEDCASE").exists()

    def test_no_match_for_different_username(self):
        """A different username finds nothing."""
        assert not users_matching_username("someoneelse").exists()


class TestClearUnconfirmedTotp(TestCase):
    """Tests for clear_unconfirmed_totp."""

    def setUp(self):
        self.user = User.objects.create_user(username="clear-user", password=PASSWORD)
        self.other_user = User.objects.create_user(username="clear-other", password=PASSWORD)

    async def test_deletes_unconfirmed_device_for_user(self):
        """The user's unfinished setup is removed."""
        await create_totp_device(self.user)

        await clear_unconfirmed_totp(self.user)

        assert not await EncryptedTOTPDevice.objects.filter(user=self.user).aexists()

    async def test_keeps_confirmed_device(self):
        """A confirmed authenticator device is not touched."""
        confirmed = await EncryptedTOTPDevice.objects.acreate(user=self.user, name=TOTP_DEVICE_NAME, confirmed=True)
        await create_totp_device(self.user)

        await clear_unconfirmed_totp(self.user)

        assert await EncryptedTOTPDevice.objects.filter(pk=confirmed.pk).aexists()
        assert await EncryptedTOTPDevice.objects.filter(user=self.user).acount() == 1

    async def test_keeps_recovery_codes(self):
        """Recovery-code devices are not touched, even unconfirmed ones."""
        recovery = await StaticDevice.objects.acreate(user=self.user, name=RECOVERY_DEVICE_NAME, confirmed=False)
        await create_totp_device(self.user)

        await clear_unconfirmed_totp(self.user)

        assert await StaticDevice.objects.filter(pk=recovery.pk).aexists()

    async def test_keeps_other_users_unconfirmed_device(self):
        """Only the given user's unfinished setup is removed."""
        other = await create_totp_device(self.other_user)
        await create_totp_device(self.user)

        await clear_unconfirmed_totp(self.user)

        assert await EncryptedTOTPDevice.objects.filter(pk=other.pk).aexists()

    async def test_no_error_when_nothing_to_clear(self):
        """Calling it with nothing pending is a harmless no-op."""
        await clear_unconfirmed_totp(self.user)

        assert not await EncryptedTOTPDevice.objects.filter(user=self.user).aexists()


class TestEnrollmentDetails(TestCase):
    """Tests for enrollment_details."""

    def setUp(self):
        self.user = User.objects.create_user(username="enroll-user", password=PASSWORD)

    async def test_returns_inline_svg_and_secret(self):
        """Returns both the QR code SVG and the manual-entry secret."""
        device = await create_totp_device(self.user)

        details = await enrollment_details(device)

        assert set(details) == {"svg", "secret"}
        assert "<svg" in details["svg"]
        assert details["secret"]

    async def test_secret_is_base32_of_device_key(self):
        """The manual-entry secret is the device's key in base32, the form authenticator apps expect."""
        device = await create_totp_device(self.user)

        details = await enrollment_details(device)

        assert details["secret"] == b32encode(device.bin_key).decode()

    async def test_secret_matches_otpauth_url(self):
        """The secret shown to the user is the same one in the QR code's otpauth URL."""
        device = await create_totp_device(self.user)

        details = await enrollment_details(device)

        query = parse_qs(urlparse(device.config_url).query)
        assert query["secret"] == [details["secret"]]


class TestConfirmDevice(TestCase):
    """Tests for confirm_device."""

    def setUp(self):
        self.user = User.objects.create_user(username="confirm-user", password=PASSWORD)

    async def test_wrong_code_keeps_device_unconfirmed(self):
        """A wrong 6-digit code returns False and leaves the device unconfirmed."""
        device = await create_totp_device(self.user)

        result = await confirm_device(device, "000000")

        assert result is False
        await device.arefresh_from_db()
        assert device.confirmed is False

    async def test_wrong_code_leaves_recovery_codes_confirmed(self):
        """Recovery codes are confirmed when created, so a wrong authenticator code doesn't change them."""
        device = await create_totp_device(self.user)
        await create_recovery_codes(self.user, confirmed=True)

        await confirm_device(device, "000000")

        assert await StaticDevice.objects.filter(user=self.user, confirmed=True).acount() == 1

    async def test_correct_code_confirms_device(self):
        """A valid code confirms the authenticator device and returns True."""
        device = await create_totp_device(self.user)

        result = await confirm_device(device, _totp_code(device))

        assert result is True
        await device.arefresh_from_db()
        assert device.confirmed is True

    async def test_correct_code_does_not_confirm_other_users_authenticator(self):
        """Confirming one user's setup leaves another user's unconfirmed authenticator device alone."""
        other_user = await _acreate_user("confirm-other")
        other_device = await create_totp_device(other_user)
        device = await create_totp_device(self.user)

        result = await confirm_device(device, _totp_code(device))

        assert result is True
        await other_device.arefresh_from_db()
        assert other_device.confirmed is False

    async def test_correct_code_leaves_recovery_codes_confirmed(self):
        """A valid code confirms only the authenticator. The recovery codes were already confirmed at creation."""
        device = await create_totp_device(self.user)
        await create_recovery_codes(self.user, confirmed=True)

        await confirm_device(device, _totp_code(device))

        assert await StaticDevice.objects.filter(user=self.user, confirmed=True).acount() == 1


class TestRenderAsync(TestCase):
    """Tests for render_async."""

    async def test_returns_response_from_render(self):
        """Returns whatever the synchronous render() produces."""
        request = MagicMock()
        expected = HttpResponse("page")

        with patch("backend.utils.authentication.render", return_value=expected) as mock_render:
            response = await render_async(request, "index.html", {"a": 1})

        assert response is expected
        mock_render.assert_called_once()

    async def test_passes_request_template_and_context_to_render(self):
        """The request, template path, and context are passed through unchanged."""
        request = MagicMock()
        context = {"name": "name"}

        with patch("backend.utils.authentication.render", return_value=HttpResponse("")) as mock_render:
            await render_async(request, "profile.html", context)

        args, kwargs = mock_render.call_args
        assert args == (request, "profile.html", context)
        assert kwargs == {"status": 200}

    async def test_passes_custom_status_code(self):
        """A non-default status code is passed to render()."""
        request = MagicMock()

        with patch("backend.utils.authentication.render", return_value=HttpResponse("", status=400)) as mock_render:
            response = await render_async(request, "profile.html", {}, status=400)

        assert response.status_code == 400
        assert mock_render.call_args.kwargs == {"status": 400}

    async def test_context_defaults_to_none(self):
        """When no context is given, None is passed to render()."""
        request = MagicMock()

        with patch("backend.utils.authentication.render", return_value=HttpResponse("")) as mock_render:
            await render_async(request, "plain.html")

        assert mock_render.call_args.args == (request, "plain.html", None)


def _client_request(ip="198.51.100.1"):
    """Return a bare POST request from this client IP, the way the login and recovery views see it."""
    return RequestFactory().post("/", REMOTE_ADDR=ip)


def _stored_username(username):
    """Return the value django-axes stores in AccessAttempt.username for this account. The plain name is never stored."""
    return settings.AXES_USERNAME_CALLABLE(RequestFactory().post("/"), {"username": username})


class TestRecordFailedLogin(TestCase):
    """Tests for record_failed_login, which counts one failed attempt from a client against a username."""

    async def test_counts_one_failure_for_the_username(self):
        """One call records one failed attempt for that username."""
        await record_failed_login(_client_request(), "counted-user")

        attempt = await AccessAttempt.objects.aget(username=_stored_username("counted-user"))
        assert attempt.failures_since_start == 1

    async def test_stores_keyed_hash_not_raw_ip(self):
        """The client is stored as the hashed identifier, never as the raw IP address."""
        await record_failed_login(_client_request("198.51.100.1"), "hashed-user")

        attempt = await AccessAttempt.objects.aget(username=_stored_username("hashed-user"))
        assert attempt.ip_address != "198.51.100.1"
        assert attempt.ip_address == settings.AXES_CLIENT_IP_CALLABLE(_client_request("198.51.100.1"))


class TestAccountLocked(TestCase):
    """Tests for account_locked, which asks django-axes whether this client may try an account."""

    async def _fail(self, username, ip, times):
        """Record failed attempts for this username from one client IP."""
        for _ in range(times):
            await record_failed_login(_client_request(ip), username)

    async def test_not_locked_before_any_failures(self):
        """A username with no failed attempts is not locked."""
        assert await account_locked(_client_request(), "fresh-user") is False

    async def test_not_locked_below_failure_limit(self):
        """Four failures, one short of the limit, don't lock the account."""
        await self._fail("below-limit-user", "198.51.100.1", 4)

        assert await account_locked(_client_request("198.51.100.1"), "below-limit-user") is False

    async def test_locked_after_failure_limit_for_same_client(self):
        """Five failures from one client lock the account for that client."""
        await self._fail("limit-user", "198.51.100.1", 5)

        assert await account_locked(_client_request("198.51.100.1"), "limit-user") is True

    async def test_other_client_is_not_locked_out(self):
        """Failures from one client don't lock the real user on a different connection."""
        await self._fail("shared-user", "198.51.100.1", 5)

        assert await account_locked(_client_request("203.0.113.9"), "shared-user") is False

    async def test_one_client_cannot_spread_guesses_across_accounts(self):
        """Five failures spread over five accounts lock that client out of other accounts too."""
        for index in range(5):
            await self._fail(f"spread-user-{index}", "198.51.100.1", 1)

        assert await account_locked(_client_request("198.51.100.1"), "untouched-user") is True
        assert await account_locked(_client_request("203.0.113.9"), "untouched-user") is False

    async def test_lock_lifts_after_cool_off(self):
        """Once the 15-minute window has passed, the lock ends."""
        await self._fail("cooloff-user", "198.51.100.1", 5)
        await AccessAttempt.objects.aupdate(attempt_time=timezone.now() - timedelta(minutes=16))

        assert await account_locked(_client_request("198.51.100.1"), "cooloff-user") is False

    async def test_lock_lifts_only_when_the_oldest_failures_age_out(self):
        """Each account's failures are kept separately, each with its own last-failure time. The lock stays until the oldest group expires."""
        await self._fail("older-user", "198.51.100.1", 3)
        await AccessAttempt.objects.filter(username=_stored_username("older-user")).aupdate(
            attempt_time=timezone.now() - timedelta(minutes=14)
        )
        await self._fail("newer-user", "198.51.100.1", 2)
        assert await account_locked(_client_request("198.51.100.1"), "untouched-user") is True

        await AccessAttempt.objects.filter(username=_stored_username("older-user")).aupdate(
            attempt_time=timezone.now() - timedelta(minutes=16)
        )

        assert await account_locked(_client_request("198.51.100.1"), "untouched-user") is False


class TestAxesLockoutBackend(TestCase):
    """Tests for AxesLockoutBackend through its async entry point, which is what the login view uses."""

    async def test_allowed_login_returns_none_so_next_backend_runs(self):
        """With no lock, the backend returns None, so Django moves on to ModelBackend for the password check."""
        result = await AxesLockoutBackend().aauthenticate(
            _client_request("198.51.100.1"), username="backend-user", password=PASSWORD
        )

        assert result is None

    async def test_locked_login_raises_permission_denied(self):
        """A locked account stops the login with AxesBackendPermissionDenied, which Django's authenticate() handles."""
        for _ in range(5):
            await record_failed_login(_client_request("198.51.100.1"), "backend-user")

        with self.assertRaises(AxesBackendPermissionDenied):
            await AxesLockoutBackend().aauthenticate(
                _client_request("198.51.100.1"), username="backend-user", password=PASSWORD
            )

    async def test_loads_session_user_so_force_login_sessions_survive(self):
        """Django's force_login() stores the first backend with get_user. Loading a user must work through this backend."""
        user = await _acreate_user("session-backend-user")

        assert await AxesLockoutBackend().aget_user(user.pk) == user
