"""Tests for the account helpers in backend.utils.account."""

from base64 import b32encode
from unittest.mock import AsyncMock

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase
from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

from backend.models import EncryptedTOTPDevice
from backend.utils.account import (
    PasswordForm,
    UsernameForm,
    check_reauth,
    has_totp,
    replace_recovery_codes,
    section_context,
    security_context,
    start_totp_setup,
    turn_off_totp,
)
from backend.utils.authentication import (
    RECOVERY_DEVICE_NAME,
    TOTP_DEVICE_NAME,
    confirmed_recovery_device,
    create_recovery_codes,
    verify_recovery_code,
)

User = get_user_model()
PASSWORD = "a-long-test-password-123"
NEW_PASSWORD = "another-long-password-456"


async def _acreate_user(username):
    """Create a user from async test code. create_user is synchronous, so it runs in a thread."""
    return await sync_to_async(User.objects.create_user)(username=username, password=PASSWORD)


def _totp_code(device):
    """Return the 6-digit code the authenticator app would show for this device right now."""
    return str(TOTP(device.bin_key, device.step, device.t0, device.digits, device.drift).token()).zfill(device.digits)


def _post_request(**data):
    """Build a POST request with the given form values."""
    return RequestFactory().post("/account/", data)


def _request_for(user, **extra):
    """Build a request whose auser() returns the given user, as the auth middleware does."""
    request = RequestFactory().get("/account/")
    request.auser = AsyncMock(return_value=user)
    for key, value in extra.items():
        setattr(request, key, value)
    return request


class TestUsernameForm(TestCase):
    """Tests for UsernameForm.clean_username."""

    def setUp(self):
        self.user = User.objects.create_user(username="CurrentName", password=PASSWORD)
        self.other = User.objects.create_user(username="OtherName", password=PASSWORD)

    def test_new_username_is_accepted(self):
        """A username no other account uses is accepted."""
        form = UsernameForm(data={"username": "fresh-name"}, instance=self.user)

        assert form.is_valid()

    def test_taken_username_is_rejected(self):
        """Another account's exact username is rejected."""
        form = UsernameForm(data={"username": "OtherName"}, instance=self.user)

        assert not form.is_valid()
        assert "A user with that username already exists." in form.errors["username"]

    def test_taken_username_in_other_case_is_rejected(self):
        """Another account's username in a different letter case is rejected."""
        form = UsernameForm(data={"username": "othername"}, instance=self.user)

        assert not form.is_valid()
        assert "A user with that username already exists." in form.errors["username"]

    def test_own_username_can_change_case(self):
        """The user can change the letter case of their own username."""
        form = UsernameForm(data={"username": "currentname"}, instance=self.user)

        assert form.is_valid()

    def test_keeping_own_username_is_accepted(self):
        """Submitting the current username unchanged is accepted."""
        form = UsernameForm(data={"username": "CurrentName"}, instance=self.user)

        assert form.is_valid()


class TestPasswordForm(TestCase):
    """Tests for PasswordForm validation and save."""

    def setUp(self):
        self.user = User.objects.create_user(username="password-form-user", password=PASSWORD)

    def _data(self, first, second=None):
        """Build form data with the given new password and confirmation."""
        return {"new_password1": first, "new_password2": second if second is not None else first}

    def test_valid_new_password_passes(self):
        """A new password that differs from the current one and matches its confirmation is valid."""
        form = PasswordForm(self.user, data=self._data(NEW_PASSWORD))

        assert form.is_valid()

    def test_mismatched_confirmation_fails(self):
        """The two new passwords must match."""
        form = PasswordForm(self.user, data=self._data(NEW_PASSWORD, "different-pass-789"))

        assert not form.is_valid()
        assert "The two passwords do not match." in form.errors["new_password2"]

    def test_reusing_current_password_fails(self):
        """The new password can't be the same as the current one."""
        form = PasswordForm(self.user, data=self._data(PASSWORD))

        assert not form.is_valid()
        assert "Choose a password that is different from your current one." in form.errors["new_password1"]

    def test_weak_password_fails_validators(self):
        """A password rejected by AUTH_PASSWORD_VALIDATORS is refused."""
        form = PasswordForm(self.user, data=self._data("123"))

        assert not form.is_valid()
        assert "new_password1" in form.errors

    def test_save_sets_new_password(self):
        """Saving changes the stored password to the new one."""
        form = PasswordForm(self.user, data=self._data(NEW_PASSWORD))
        assert form.is_valid()

        form.save()

        self.user.refresh_from_db()
        assert self.user.check_password(NEW_PASSWORD)
        assert not self.user.check_password(PASSWORD)

    def test_save_returns_user(self):
        """save() returns the updated user."""
        form = PasswordForm(self.user, data=self._data(NEW_PASSWORD))
        assert form.is_valid()

        assert form.save() == self.user


class TestStartTotpSetup(TestCase):
    """Tests for start_totp_setup."""

    async def test_creates_unconfirmed_device(self):
        """Starting a setup creates a new unconfirmed authenticator device."""
        user = await _acreate_user("setup-new-user")

        device = await start_totp_setup(user)

        assert device.confirmed is False
        assert device.name == TOTP_DEVICE_NAME
        assert await EncryptedTOTPDevice.objects.filter(pk=device.pk).aexists()

    async def test_replaces_earlier_unfinished_setup(self):
        """An older unfinished setup is removed, leaving only the new one."""
        user = await _acreate_user("setup-replace-user")
        old = await EncryptedTOTPDevice.objects.acreate(user=user, name=TOTP_DEVICE_NAME, confirmed=False)

        new = await start_totp_setup(user)

        assert not await EncryptedTOTPDevice.objects.filter(pk=old.pk).aexists()
        assert await EncryptedTOTPDevice.objects.filter(user=user, confirmed=False).acount() == 1
        assert new.pk != old.pk

    async def test_keeps_confirmed_authenticator(self):
        """An active authenticator is not removed when a new setup starts."""
        user = await _acreate_user("setup-keep-user")
        confirmed = await EncryptedTOTPDevice.objects.acreate(user=user, name=TOTP_DEVICE_NAME, confirmed=True)

        await start_totp_setup(user)

        assert await EncryptedTOTPDevice.objects.filter(pk=confirmed.pk).aexists()


class TestTurnOffTotp(TestCase):
    """Tests for turn_off_totp."""

    async def test_removes_confirmed_authenticator(self):
        """The active authenticator is removed."""
        user = await _acreate_user("off-confirmed-user")
        device = await EncryptedTOTPDevice.objects.acreate(user=user, name=TOTP_DEVICE_NAME, confirmed=True)

        await turn_off_totp(user)

        assert not await EncryptedTOTPDevice.objects.filter(pk=device.pk).aexists()

    async def test_removes_unconfirmed_authenticator(self):
        """An unfinished setup is removed too."""
        user = await _acreate_user("off-unconfirmed-user")
        device = await EncryptedTOTPDevice.objects.acreate(user=user, name=TOTP_DEVICE_NAME, confirmed=False)

        await turn_off_totp(user)

        assert not await EncryptedTOTPDevice.objects.filter(pk=device.pk).aexists()

    async def test_keeps_recovery_codes(self):
        """Recovery codes stay on the account when the authenticator is turned off."""
        user = await _acreate_user("off-recovery-user")
        await create_recovery_codes(user, confirmed=True)
        await EncryptedTOTPDevice.objects.acreate(user=user, name=TOTP_DEVICE_NAME, confirmed=True)

        await turn_off_totp(user)

        assert await confirmed_recovery_device(user) is not None

    async def test_leaves_other_users_authenticators(self):
        """Another user's authenticator is not affected."""
        user = await _acreate_user("off-owner-user")
        other = await _acreate_user("off-other-user")
        other_device = await EncryptedTOTPDevice.objects.acreate(user=other, name=TOTP_DEVICE_NAME, confirmed=True)

        await turn_off_totp(user)

        assert await EncryptedTOTPDevice.objects.filter(pk=other_device.pk).aexists()


class TestReplaceRecoveryCodes(TestCase):
    """Tests for replace_recovery_codes."""

    async def test_returns_ten_new_codes(self):
        """A new set of ten plain-text codes is returned."""
        user = await _acreate_user("replace-count-user")

        codes = await replace_recovery_codes(user)

        assert len(codes) == 10
        assert len(set(codes)) == 10

    async def test_creates_confirmed_recovery_device(self):
        """The new recovery-code device is confirmed right away."""
        user = await _acreate_user("replace-confirmed-user")

        await replace_recovery_codes(user)

        device = await confirmed_recovery_device(user)
        assert device is not None
        assert device.name == RECOVERY_DEVICE_NAME

    async def test_deletes_old_recovery_device(self):
        """The previous recovery-code device is removed."""
        user = await _acreate_user("replace-old-user")
        await create_recovery_codes(user, confirmed=True)
        old = await confirmed_recovery_device(user)

        await replace_recovery_codes(user)

        assert not await StaticDevice.objects.filter(pk=old.pk).aexists()
        assert await StaticDevice.objects.filter(user=user).acount() == 1

    async def test_old_codes_stop_working(self):
        """A code from before the replacement is refused."""
        user = await _acreate_user("replace-stale-user")
        old_codes = await create_recovery_codes(user, confirmed=True)

        await replace_recovery_codes(user)

        device = await confirmed_recovery_device(user)
        assert await verify_recovery_code(device, old_codes[0]) is False

    async def test_new_codes_work(self):
        """A code from the new set can be used."""
        user = await _acreate_user("replace-new-user")
        codes = await replace_recovery_codes(user)

        device = await confirmed_recovery_device(user)
        assert await verify_recovery_code(device, codes[0]) is True

    async def test_leaves_no_old_tokens_behind(self):
        """Tokens from the old set are removed along with their device."""
        user = await _acreate_user("replace-tokens-user")
        await create_recovery_codes(user, confirmed=True)
        before = await StaticToken.objects.filter(device__user=user).acount()

        await replace_recovery_codes(user)

        assert before == 10
        assert await StaticToken.objects.filter(device__user=user).acount() == 10


class TestHasTotp(TestCase):
    """Tests for has_totp."""

    async def test_false_without_authenticator(self):
        """A user with no authenticator app doesn't have TOTP."""
        user = await _acreate_user("has-none-user")

        assert await has_totp(user) is False

    async def test_false_for_unconfirmed_authenticator(self):
        """An unfinished setup doesn't count as having TOTP."""
        user = await _acreate_user("has-unconfirmed-user")
        await EncryptedTOTPDevice.objects.acreate(user=user, name=TOTP_DEVICE_NAME, confirmed=False)

        assert await has_totp(user) is False

    async def test_true_for_confirmed_authenticator(self):
        """A confirmed authenticator means TOTP is on."""
        user = await _acreate_user("has-confirmed-user")
        await EncryptedTOTPDevice.objects.acreate(user=user, name=TOTP_DEVICE_NAME, confirmed=True)

        assert await has_totp(user) is True


class TestCheckReauth(TestCase):
    """Tests for check_reauth."""

    async def _user_with_totp(self, username):
        """Create a user with a confirmed authenticator app and return the user and the device."""
        user = await _acreate_user(username)
        device = await EncryptedTOTPDevice.objects.acreate(user=user, name=TOTP_DEVICE_NAME, confirmed=True)
        return user, device

    async def _user_with_recovery(self, username):
        """Create a user with a confirmed recovery code set and return the user and the codes."""
        user = await _acreate_user(username)
        codes = await create_recovery_codes(user, confirmed=True)
        return user, codes

    async def test_correct_password_passes_without_totp(self):
        """With no authenticator app, the correct password is enough."""
        user = await _acreate_user("reauth-pass-user")

        error = await check_reauth(_post_request(password=PASSWORD), user)

        assert error is None

    async def test_missing_password_is_an_error(self):
        """An empty password is refused."""
        user = await _acreate_user("reauth-missing-user")

        error = await check_reauth(_post_request(password=""), user)

        assert error == "Enter your password to confirm."

    async def test_wrong_password_is_an_error(self):
        """A wrong password is refused."""
        user = await _acreate_user("reauth-wrong-user")

        error = await check_reauth(_post_request(password="not-the-password"), user)

        assert error == "That password is not correct."

    async def test_totp_required_when_authenticator_is_on(self):
        """With an authenticator app on, a correct password alone is not enough."""
        user, _ = await self._user_with_totp("reauth-totp-required-user")

        error = await check_reauth(_post_request(password=PASSWORD), user)

        assert error == "Enter the 6-digit code from your authenticator app."

    async def test_totp_required_message_mentions_recovery_when_allowed(self):
        """When recovery codes are accepted here, the message also offers them."""
        user, _ = await self._user_with_totp("reauth-totp-recovery-msg-user")

        error = await check_reauth(_post_request(password=PASSWORD), user, allow_recovery_code=True)

        assert error == (
            "Enter the 6-digit code from your authenticator app, or use a recovery code instead of your password."
        )

    async def test_wrong_totp_code_is_an_error(self):
        """A wrong authenticator code is refused."""
        user, _ = await self._user_with_totp("reauth-wrong-code-user")

        error = await check_reauth(_post_request(password=PASSWORD, otp_token="000000"), user)

        assert error == "That verification code is not correct."

    async def test_correct_totp_code_passes(self):
        """A correct password and a valid authenticator code pass."""
        user, device = await self._user_with_totp("reauth-good-code-user")

        error = await check_reauth(_post_request(password=PASSWORD, otp_token=_totp_code(device)), user)

        assert error is None

    async def test_totp_code_is_stripped_of_spaces(self):
        """A code with stray spaces still passes."""
        user, device = await self._user_with_totp("reauth-space-code-user")

        error = await check_reauth(_post_request(password=PASSWORD, otp_token=f" {_totp_code(device)} "), user)

        assert error is None

    async def test_both_totp_and_recovery_code_is_an_error(self):
        """Giving both an authenticator code and a recovery code is refused."""
        user, codes = await self._user_with_recovery("reauth-both-user")

        error = await check_reauth(
            _post_request(password=PASSWORD, otp_token="123456", recovery_code=codes[0]),
            user,
            allow_recovery_code=True,
        )

        assert error == "Enter either your password and an authenticator code, or a recovery code on its own, not both."

    async def test_recovery_code_with_totp_code_and_no_password_is_refused(self):
        """A recovery code sent with an authenticator code, and no password, is refused and the code is kept."""
        user, codes = await self._user_with_recovery("reauth-recovery-totp-user")

        error = await check_reauth(
            _post_request(otp_token="123456", recovery_code=codes[0]),
            user,
            allow_recovery_code=True,
        )

        assert error == "Enter either your password and an authenticator code, or a recovery code on its own, not both."
        device = await confirmed_recovery_device(user)
        assert await verify_recovery_code(device, codes[0]) is True

    async def test_both_codes_does_not_use_up_recovery_code(self):
        """Entering both kinds of code is refused before the recovery code is checked, so it isn't used up."""
        user, codes = await self._user_with_recovery("reauth-both-keep-user")

        await check_reauth(
            _post_request(password=PASSWORD, otp_token="123456", recovery_code=codes[0]),
            user,
            allow_recovery_code=True,
        )

        device = await confirmed_recovery_device(user)
        assert await verify_recovery_code(device, codes[0]) is True

    async def test_recovery_code_is_used_without_password(self):
        """When allowed, a valid recovery code replaces the password and the authenticator code."""
        user, codes = await self._user_with_recovery("reauth-recovery-user")

        error = await check_reauth(_post_request(recovery_code=codes[0]), user, allow_recovery_code=True)

        assert error is None

    async def test_password_with_recovery_code_is_refused(self):
        """A password sent with a recovery code is refused, and the recovery code is not used up."""
        user, codes = await self._user_with_recovery("reauth-pw-and-recovery-user")

        error = await check_reauth(
            _post_request(password=PASSWORD, recovery_code=codes[0]), user, allow_recovery_code=True
        )

        assert error == "Enter either your password and an authenticator code, or a recovery code on its own, not both."
        device = await confirmed_recovery_device(user)
        assert await verify_recovery_code(device, codes[0]) is True

    async def test_recovery_code_is_consumed_when_used(self):
        """A recovery code accepted here can't be used a second time."""
        user, codes = await self._user_with_recovery("reauth-consumed-user")
        await check_reauth(_post_request(recovery_code=codes[0]), user, allow_recovery_code=True)

        error = await check_reauth(_post_request(recovery_code=codes[0]), user, allow_recovery_code=True)

        assert error == "That recovery code is not correct."

    async def test_wrong_recovery_code_is_an_error(self):
        """An unknown recovery code is refused."""
        user, _ = await self._user_with_recovery("reauth-wrong-recovery-user")

        error = await check_reauth(_post_request(recovery_code="zzzz9999"), user, allow_recovery_code=True)

        assert error == "That recovery code is not correct."

    async def test_recovery_code_without_recovery_device_is_an_error(self):
        """A recovery code is refused if the account has no recovery codes."""
        user = await _acreate_user("reauth-no-codes-user")

        error = await check_reauth(_post_request(recovery_code="abcd1234"), user, allow_recovery_code=True)

        assert error == "That recovery code is not correct."

    async def test_recovery_code_ignored_when_not_allowed(self):
        """Without allow_recovery_code, a recovery code is ignored and the password is required."""
        user, codes = await self._user_with_recovery("reauth-not-allowed-user")

        error = await check_reauth(_post_request(recovery_code=codes[0]), user)

        assert error == "Enter your password to confirm."

    async def test_recovery_code_not_consumed_when_not_allowed(self):
        """A recovery code sent where it isn't allowed is left unused."""
        user, codes = await self._user_with_recovery("reauth-not-allowed-keep-user")

        await check_reauth(_post_request(recovery_code=codes[0]), user)

        device = await confirmed_recovery_device(user)
        assert await verify_recovery_code(device, codes[0]) is True


class TestSectionContext(TestCase):
    """Tests for section_context."""

    async def test_includes_username_form_and_has_totp(self):
        """The Account section gets the username form and the TOTP flag."""
        user = await _acreate_user("section-user")
        request = _request_for(user)

        context = await section_context(request)

        assert isinstance(context["form"], UsernameForm)
        assert context["form"].instance == user
        assert context["has_totp"] is False

    async def test_has_totp_true_when_authenticator_on(self):
        """has_totp reflects a confirmed authenticator app."""
        user = await _acreate_user("section-totp-user")
        await EncryptedTOTPDevice.objects.acreate(user=user, name=TOTP_DEVICE_NAME, confirmed=True)

        context = await section_context(_request_for(user))

        assert context["has_totp"] is True

    async def test_extra_values_are_added(self):
        """Extra values such as error messages are added to the context."""
        user = await _acreate_user("section-extra-user")

        context = await section_context(_request_for(user), error="Oops", status_note="x")

        assert context["error"] == "Oops"
        assert context["status_note"] == "x"


class TestSecurityContext(TestCase):
    """Tests for security_context."""

    async def test_includes_password_form_and_has_totp(self):
        """The Security section gets an unbound password form and the TOTP flag."""
        user = await _acreate_user("security-user")

        context = await security_context(_request_for(user))

        assert isinstance(context["password_form"], PasswordForm)
        assert context["password_form"].is_bound is False
        assert context["has_totp"] is False

    async def test_no_pending_setup_has_no_pending_values(self):
        """Without an unfinished setup, pending_totp is None and there is no QR code."""
        user = await _acreate_user("security-nopending-user")

        context = await security_context(_request_for(user))

        assert context["pending_totp"] is None
        assert "svg" not in context
        assert "secret" not in context

    async def test_pending_setup_includes_qr_and_secret(self):
        """An unfinished setup adds its device, QR code, and manual secret to the context."""
        user = await _acreate_user("security-pending-user")
        device = await EncryptedTOTPDevice.objects.acreate(user=user, name=TOTP_DEVICE_NAME, confirmed=False)

        context = await security_context(_request_for(user))

        assert context["pending_totp"].pk == device.pk
        assert "<svg" in context["svg"]
        assert context["secret"] == b32encode(device.bin_key).decode()

    async def test_extra_values_are_added(self):
        """Extra values such as error messages are added on top."""
        user = await _acreate_user("security-extra-user")

        context = await security_context(_request_for(user), totp_message="Two-factor authentication is on.")

        assert context["totp_message"] == "Two-factor authentication is on."
