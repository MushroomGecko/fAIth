from django_otp.plugins.otp_totp.models import TOTPDevice


async def authenticator_device_id(user):
    """Return the persistent ID of the user's confirmed authenticator app device, or None."""
    device = await TOTPDevice.objects.filter(user=user, confirmed=True).order_by("id").afirst()
    return device.persistent_id if device else None
