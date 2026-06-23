"""
Structured exception hierarchy.

Services raise these; api/v1/routes never raise raw HTTPException for domain
errors, and main.py registers exception handlers that translate each type to
a consistent JSON error shape: {"error": "<code>", "message": "<human text>"}.
This keeps "why did this fail" traceable instead of generic 500s, which
matters a lot for an app making medical-adjacent claims.
"""


class AcneTrexError(Exception):
    status_code: int = 500
    code: str = "internal_error"

    def __init__(self, message: str, *, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class AuthError(AcneTrexError):
    status_code = 401
    code = "auth_error"


class InvalidCredentialsError(AuthError):
    code = "invalid_credentials"


class SessionExpiredError(AuthError):
    code = "session_expired"


class AccountExistsError(AcneTrexError):
    status_code = 409
    code = "account_exists"


class NotFoundError(AcneTrexError):
    status_code = 404
    code = "not_found"


class ValidationFailedError(AcneTrexError):
    status_code = 422
    code = "validation_failed"


class ConsentRequiredError(AcneTrexError):
    status_code = 403
    code = "consent_required"


class InsufficientDataError(AcneTrexError):
    """Raised when an ML service is asked to produce output without enough
    real history to support it. The correct response is to say so, not to
    fabricate a confident answer."""
    status_code = 422
    code = "insufficient_data"


class MLServiceError(AcneTrexError):
    status_code = 422
    code = "ml_service_error"


class MigrationError(AcneTrexError):
    status_code = 422
    code = "migration_error"


class RateLimitedError(AcneTrexError):
    status_code = 429
    code = "rate_limited"


class NotImplementedYetError(AcneTrexError):
    """Used by route stubs for endpoints whose contract is defined but whose
    real service implementation is scheduled for a later phase. Returning
    this honestly (501, explicit message) is the deliberate alternative to
    returning a fabricated 200 response with fake data."""
    status_code = 501
    code = "not_implemented_yet"
