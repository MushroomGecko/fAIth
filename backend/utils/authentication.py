from django_otp.plugins.otp_totp.models import TOTPDevice


async def authenticator_device_id(user):
    """
    Return the persistent ID of the user's confirmed authenticator app device.

    Parameters:
        user (User): The user whose authenticator device to look up.

    Returns:
        str | None: The device's persistent ID, or None if the user has no confirmed authenticator app.
    """
    # Only confirmed devices can be used to log in. The oldest one is used if there are several.
    device = await TOTPDevice.objects.filter(user=user, confirmed=True).order_by("id").afirst()
    # The persistent ID is "<model>/<id>". The login form uses it to pick the device.
    return device.persistent_id if device else None
