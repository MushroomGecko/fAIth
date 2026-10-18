"""Tests for the account recovery helpers in backend.utils.recover."""

from unittest.mock import AsyncMock, MagicMock, patch

from asgiref.sync import sync_to_async
from django.contrib.auth import get_user_model
from django.contrib.sessions.backends.db import SessionStore
from django.http import HttpResponse
from django.test import TestCase
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

from backend.utils.account import PasswordForm
from backend.utils.authentication import (
    RECOVERY_DEVICE_NAME,
    TOTP_DEVICE_NAME,
    confirmed_recovery_device,
    create_recovery_codes,
    verify_recovery_code,
)
from backend.utils.recover import (
    blank_recovery_user,
    recovery_password_form,
    render_recovery_page,
    reset_second_factor,
)
from backend.utils.signup import read_pending_device_id

User = get_user_model()
PASSWORD = "a-long-test-password-123"
NEW_PASSWORD = "another-long-password-456"


async def _acreate_user(username):
    """Create a user from async test code. create_user is synchronous, so it runs in a thread."""
    return await sync_to_async(User.objects.create_user)(username=username, password=PASSWORD)


class TestBlankRecoveryUser(TestCase):
    """Tests for blank_recovery_user."""

    async def test_returns_unsaved_user(self):
        """The stand-in user has no primary key, so it's never saved."""
        user = await blank_recovery_user()

        assert isinstance(user, User)
        assert user.pk is None

    async def test_has_no_username_and_matches_no_password(self):
        """The stand-in has no username, and no password matches it."""
        user = await blank_recovery_user()

        assert user.username == ""
        assert not user.check_password("")
        assert not user.check_password(PASSWORD)

    async def test_does_not_write_to_database(self):
        """Creating the stand-in doesn't add a row to the users table."""
        before = await User.objects.acount()

        await blank_recovery_user()

        assert await User.objects.acount() == before


class TestRecoveryPasswordForm(TestCase):
    """Tests for recovery_password_form."""

    async def test_returns_password_form_for_user(self):
        """The form is built for the given user."""
        user = await _acreate_user("form-user")

        form = await recovery_password_form(user)

        assert isinstance(form, PasswordForm)
        assert form.user == user

    async def test_without_data_form_is_unbound(self):
        """With no POST data, the form is unbound, so it's shown empty and not validated."""
        user = await _acreate_user("unbound-user")

        form = await recovery_password_form(user)

        assert form.is_bound is False

    async def test_with_data_form_is_bound(self):
        """With POST data, the form is bound and can be validated."""
        user = await _acreate_user("bound-user")

        form = await recovery_password_form(user, {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD})

        assert form.is_bound is True

    async def test_valid_new_password_passes(self):
        """A new password that is different from the current one and matches its confirmation is valid."""
        user = await _acreate_user("valid-form-user")
        form = await recovery_password_form(user, {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD})

        assert await sync_to_async(form.is_valid)()

    async def test_mismatched_passwords_fail(self):
        """The two new passwords must match."""
        user = await _acreate_user("mismatch-form-user")
        form = await recovery_password_form(
            user, {"new_password1": NEW_PASSWORD, "new_password2": "different-pass-789"}
        )

        assert not await sync_to_async(form.is_valid)()
        assert "new_password2" in form.errors

    async def test_reusing_current_password_fails(self):
        """A recovery can't set the password back to the one that's already on the account."""
        user = await _acreate_user("reuse-form-user")
        form = await recovery_password_form(user, {"new_password1": PASSWORD, "new_password2": PASSWORD})

        assert not await sync_to_async(form.is_valid)()
        assert "new_password1" in form.errors

    async def test_blank_user_form_accepts_new_password(self):
        """The stand-in user has no password to match against, so a new password is accepted."""
        user = await blank_recovery_user()
        form = await recovery_password_form(user, {"new_password1": NEW_PASSWORD, "new_password2": NEW_PASSWORD})

        assert await sync_to_async(form.is_valid)()


class TestResetSecondFactor(TestCase):
    """Tests for reset_second_factor."""

    async def test_removes_existing_authenticator_device(self):
        """The confirmed authenticator app is turned off."""
        user = await _acreate_user("reset-totp-user")
        old = await TOTPDevice.objects.acreate(user=user, name=TOTP_DEVICE_NAME, confirmed=True)

        await reset_second_factor(user, SessionStore())

        assert not await TOTPDevice.objects.filter(pk=old.pk).aexists()

    async def test_replaces_recovery_codes(self):
        """The old recovery-code device and its tokens are deleted, and a new one is created."""
        user = await _acreate_user("reset-codes-user")
        await create_recovery_codes(user, confirmed=True)
        old_device = await confirmed_recovery_device(user)

        await reset_second_factor(user, SessionStore())

        assert not await StaticDevice.objects.filter(pk=old_device.pk).aexists()
        new_device = await confirmed_recovery_device(user)
        assert new_device is not None
        assert new_device.pk != old_device.pk
        assert new_device.name == RECOVERY_DEVICE_NAME

    async def test_old_recovery_codes_no_longer_work(self):
        """A code from before the reset is refused afterward."""
        user = await _acreate_user("reset-old-code-user")
        old_codes = await create_recovery_codes(user, confirmed=True)

        await reset_second_factor(user, SessionStore())

        new_device = await confirmed_recovery_device(user)
        assert await verify_recovery_code(new_device, old_codes[0]) is False

    async def test_returns_ten_new_recovery_codes(self):
        """The returned codes are the fresh set, one for each code the account now has."""
        user = await _acreate_user("reset-return-codes-user")
        await create_recovery_codes(user, confirmed=True)

        _, codes = await reset_second_factor(user, SessionStore())

        assert len(codes) == 10
        new_device = await confirmed_recovery_device(user)
        assert await StaticDevice.objects.filter(pk=new_device.pk, confirmed=True).aexists()

    async def test_new_recovery_codes_work_once(self):
        """A returned code can be used to recover, and then it's used up."""
        user = await _acreate_user("reset-new-code-user")

        _, codes = await reset_second_factor(user, SessionStore())

        device = await confirmed_recovery_device(user)
        assert await verify_recovery_code(device, codes[0]) is True
        assert await verify_recovery_code(device, codes[0]) is False

    async def test_creates_unconfirmed_authenticator_device(self):
        """A new authenticator device is created for setup, and it starts unconfirmed."""
        user = await _acreate_user("reset-new-totp-user")

        totp, _ = await reset_second_factor(user, SessionStore())

        assert totp.user_id == user.pk
        assert totp.name == TOTP_DEVICE_NAME
        assert totp.confirmed is False
        assert await TOTPDevice.objects.filter(pk=totp.pk, confirmed=False).aexists()

    async def test_stores_new_device_as_pending_enrollment(self):
        """The new authenticator device is stored in the session so the setup step can confirm or skip it."""
        user = await _acreate_user("reset-pending-user")
        session = SessionStore()

        totp, _ = await reset_second_factor(user, session)

        assert await read_pending_device_id(session) == totp.id

    async def test_stores_new_codes_in_pending_enrollment(self):
        """The new recovery codes are also kept in the session, so the setup page can show them."""
        user = await _acreate_user("reset-pending-codes-user")
        session = SessionStore()

        _, codes = await reset_second_factor(user, session)

        assert await session.aget("pending_recovery_codes") == codes

    async def test_leaves_other_users_devices_alone(self):
        """Another user's authenticator and recovery codes are not touched."""
        user = await _acreate_user("reset-owner-user")
        other = await _acreate_user("reset-other-user")
        other_totp = await TOTPDevice.objects.acreate(user=other, name=TOTP_DEVICE_NAME, confirmed=True)
        await create_recovery_codes(other, confirmed=True)
        other_recovery = await confirmed_recovery_device(other)

        await reset_second_factor(user, SessionStore())

        assert await TOTPDevice.objects.filter(pk=other_totp.pk).aexists()
        assert await StaticDevice.objects.filter(pk=other_recovery.pk).aexists()


class TestRenderRecoveryPage(TestCase):
    """Tests for render_recovery_page."""

    async def test_passes_form_username_and_error_in_context(self):
        """The form, username, and error message are passed to the template."""
        form = MagicMock()
        page = HttpResponse("recover")

        with patch("backend.utils.recover.render_async", new_callable=AsyncMock, return_value=page) as mock_render:
            response = await render_recovery_page(MagicMock(), "recover.html", form, username="name", error="Nope")

        assert response is page
        args, kwargs = mock_render.call_args
        assert args[1] == "recover.html"
        assert args[2] == {"form": form, "username": "name", "error": "Nope"}
        assert kwargs == {"status": 200}

    async def test_defaults_are_empty_username_and_no_error(self):
        """With no username or error given, the context uses an empty username and no error."""
        with patch(
            "backend.utils.recover.render_async", new_callable=AsyncMock, return_value=HttpResponse("")
        ) as mock_render:
            await render_recovery_page(MagicMock(), "recover.html", MagicMock())

        context = mock_render.call_args.args[2]
        assert context["username"] == ""
        assert context["error"] is None

    async def test_passes_custom_status(self):
        """A custom status code, such as 400 for a failed check, is passed to the renderer."""
        with patch(
            "backend.utils.recover.render_async", new_callable=AsyncMock, return_value=HttpResponse("")
        ) as mock_render:
            await render_recovery_page(MagicMock(), "recover.html", MagicMock(), status=400)

        assert mock_render.call_args.kwargs == {"status": 400}
