from urllib.parse import parse_qs, urlparse

import segno
from asgiref.sync import sync_to_async
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken
from django_otp.plugins.otp_totp.models import TOTPDevice

RECOVERY_CODE_COUNT = 10
PENDING_DEVICE_SESSION_KEY = "pending_totp_device_id"
PENDING_CODES_SESSION_KEY = "pending_recovery_codes"
ENROLLMENT_STEP = "authenticate"
INVALID_CODE_MESSAGE = "That code wasn't valid. Check your authenticator app and try again."


async def create_user_and_devices(form):
    """Save the user and create unconfirmed TOTP and recovery-code devices."""
    # Django's form.save() has no async version, so run it in a thread.
    user = await sync_to_async(form.save, thread_sensitive=True)()
    # The device names appear in the login device dropdown, so they should read clearly.
    totp = await TOTPDevice.objects.acreate(user=user, name="Authenticator app", confirmed=False)
    static = await StaticDevice.objects.acreate(user=user, name="Recovery code", confirmed=False)
    codes = [StaticToken.random_token() for _ in range(RECOVERY_CODE_COUNT)]
    await StaticToken.objects.abulk_create([StaticToken(device=static, token=code) for code in codes])
    return totp, codes


async def pending_device(device_id):
    """Return the unconfirmed TOTP device for this enrollment, if any."""
    if device_id is None:
        return None
    return await TOTPDevice.objects.filter(id=device_id, confirmed=False).select_related("user").afirst()


async def confirm_device(device, token):
    """Confirm the TOTP device and recovery codes if the token is valid."""
    # django-otp's verify_token has no async version, so run it in a thread.
    if not await sync_to_async(device.verify_token, thread_sensitive=True)(token):
        return False
    device.confirmed = True
    await device.asave(update_fields=["confirmed"])
    await StaticDevice.objects.filter(user_id=device.user_id, confirmed=False).aupdate(confirmed=True)
    return True


async def store_pending_device(session, device_id, codes):
    """Remember the pending enrollment for this browser session until it's confirmed."""
    await session.aset(PENDING_DEVICE_SESSION_KEY, device_id)
    await session.aset(PENDING_CODES_SESSION_KEY, codes)


async def read_pending_device_id(session):
    """Read the pending TOTP device ID from the session."""
    return await session.aget(PENDING_DEVICE_SESSION_KEY)


async def read_pending_codes(session):
    """Read the recovery codes generated for this enrollment."""
    return await session.aget(PENDING_CODES_SESSION_KEY) or []


async def load_pending_enrollment(session):
    """Return the pending TOTP device and recovery codes for this session, or (None, [])."""
    device = await pending_device(await read_pending_device_id(session))
    return device, await read_pending_codes(session)


async def clear_pending_device(session):
    """Forget the pending enrollment once it's confirmed."""
    await session.apop(PENDING_DEVICE_SESSION_KEY, None)
    await session.apop(PENDING_CODES_SESSION_KEY, None)


def enrollment_details(device):
    """Return the QR code as inline SVG and the base32 secret for manual entry.

    Both are generated on the server from the device's otpauth URL. This is pure computation,
    so it stays synchronous.
    """
    config_url = device.config_url
    secret = parse_qs(urlparse(config_url).query)["secret"][0]
    svg = segno.make(config_url, error="m").svg_inline(scale=5)
    return {"svg": svg, "secret": secret}
