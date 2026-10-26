# Import every model here so Django registers it for the backend app.
from backend.models.encrypted_totp import EncryptedTOTPDevice
from backend.models.user import User

__all__ = ["EncryptedTOTPDevice", "User"]
