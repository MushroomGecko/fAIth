# Import every model here so Django registers it for the backend app.
from backend.models.encrypted_totp import EncryptedTOTPDevice

__all__ = ["EncryptedTOTPDevice"]
