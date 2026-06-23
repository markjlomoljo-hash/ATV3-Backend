"""
Validation / Acceptance Engine.

No ML or AI output reaches the user without passing through here first. This
is the single place that decides "insufficient_data" vs "low_confidence" vs
"passed" vs "failed" - every pipeline (face, forecast, product, assistant)
calls into this instead of inventing its own ad-hoc threshold check, so the
rule "never fabricate certainty" is enforced consistently rather than
per-feature.
"""
from app.core.config import settings
from app.core.constants import ValidationStatus
from app.core.errors import InsufficientDataError


def validate_image_metrics(quality_score: float, is_valid_face: bool, confidence_score: float) -> str:
    if not is_valid_face:
        return ValidationStatus.FAILED.value
    if quality_score < settings.MIN_IMAGE_QUALITY_SCORE:
        return ValidationStatus.INSUFFICIENT_DATA.value
    if confidence_score < settings.MIN_FACE_CONFIDENCE:
        return ValidationStatus.LOW_CONFIDENCE.value
    return ValidationStatus.PASSED.value


def validate_forecast_data_density(history_points: int) -> str:
    if history_points < settings.FORECAST_MIN_DAYS_REQUIRED:
        return ValidationStatus.INSUFFICIENT_DATA.value
    return ValidationStatus.PASSED.value


def require_forecast_data_density(history_points: int) -> None:
    if history_points < settings.FORECAST_MIN_DAYS_REQUIRED:
        raise InsufficientDataError(
            f"At least {settings.FORECAST_MIN_DAYS_REQUIRED} days of logged history are needed for a forecast. "
            f"You currently have {history_points}. Keep logging daily and check back."
        )


def validate_product_analysis(ingredient_count: int) -> str:
    if ingredient_count == 0:
        return ValidationStatus.INSUFFICIENT_DATA.value
    if ingredient_count < 2:
        return ValidationStatus.LOW_CONFIDENCE.value
    return ValidationStatus.PASSED.value


def validate_assistant_response(has_context: bool, self_check_passed: bool | None) -> str:
    if not has_context:
        return ValidationStatus.INSUFFICIENT_DATA.value
    if self_check_passed is False:
        return ValidationStatus.LOW_CONFIDENCE.value
    return ValidationStatus.PASSED.value
