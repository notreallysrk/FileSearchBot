# THIS SOURCE CODE IS DEVELOPED BY @MIGHTYAYUSH. FOLLOW @SOCIAL_BOTS FOR MORE DETAILS AND MEET THE DEVELOPER...
from typing import Optional

class AppError(Exception):

    def __init__(self, message: str, user_facing: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.user_facing = user_facing or "An unexpected internal error occurred. Please try again later."

class DatabaseError(AppError):

    pass

class ManifestError(AppError):

    pass

class ManifestCorruptError(ManifestError):

    pass

class ManifestUploadError(ManifestError):

    pass

class TokenError(AppError):

    pass

class TokenExpiredError(TokenError):

    def __init__(self, message: str = "This file link has expired."):
        super().__init__(message, user_facing=message)

class TokenInvalidError(TokenError):

    def __init__(self, message: str = "Invalid, malformed, or unknown file link."):
        super().__init__(message, user_facing=message)

class DeliveryError(AppError):

    pass

class SubscriptionRequiredError(AppError):

    def __init__(self, message: str = "Please join our required channels to use this bot."):
        super().__init__(message, user_facing=message)

class RateLimitExceededError(AppError):

    def __init__(self, retry_after: float = 1.0):
        msg = f"You are doing that too fast. Please slow down ({retry_after:.1f}s)."
        super().__init__(msg, user_facing=msg)
        self.retry_after = retry_after

class UserBlockedError(AppError):

    def __init__(self, message: str = "You have been blocked from using this service."):
        super().__init__(message, user_facing=message)
