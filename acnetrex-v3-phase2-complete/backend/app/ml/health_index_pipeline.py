"""
Cutis Health Index (CHI) pipeline.

This is a line-for-line port of the real `ZW` function found in the
recovered v2 bundle (deployed-bundle.pretty.js, ~line 29473), not a
reinvented scoring system. It's a transparent, explainable weighted-baseline
model - exactly the kind of model the spec calls for as a starting point
("AI/ML-ready design for future accuracy improvements"). The six components
and their weights, the clamp ranges, and the status thresholds are all
preserved exactly so historical Cutis Health Index values stay comparable
across the v2 -> v3 upgrade instead of jumping discontinuously because the
math changed.
"""
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from app.core.constants import HealthIndexStatus


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


@dataclass
class ScanPoint:
    captured_at: datetime
    lesion_count: float = 0.0
    redness_score: float = 0.0
    oiliness_score: float = 0.0
    dryness_score: float = 0.0


@dataclass
class SleepPoint:
    log_date: datetime
    net_sleep_hours: float


@dataclass
class FoodPoint:
    log_date: datetime
    glycemic_load: float
    overall_risk: float


@dataclass
class StressPoint:
    log_date: datetime
    stress_level: float


def compute_health_index(
    all_scans: list[ScanPoint],
    all_sleep: list[SleepPoint],
    all_food: list[FoodPoint],
    all_stress: list[StressPoint],
    high_irritation_routine_product_count: int,
    skin_type: str | None,
    now: datetime | None = None,
) -> dict:
    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)

    recent_scans = [s for s in all_scans if s.captured_at >= cutoff]
    recent_sleep = [s for s in all_sleep if s.log_date >= cutoff]
    recent_food = [s for s in all_food if s.log_date >= cutoff]
    recent_stress = [s for s in all_stress if s.log_date >= cutoff]
    w = high_irritation_routine_product_count  # "w" in the original

    # --- barrierIntegrity ("g" in the original) ---
    barrier = 70.0
    barrier -= w * 8
    if recent_scans:
        barrier -= _avg([s.dryness_score for s in recent_scans]) * 0.3
    if recent_sleep:
        avg_sleep = _avg([s.net_sleep_hours for s in recent_sleep])
        if avg_sleep < 6:
            barrier -= 12
        elif avg_sleep >= 7.5:
            barrier += 5
    barrier = _clamp(barrier, 10, 100)

    # --- inflammationLoad ("j" in the original, via inverse "S") ---
    inflammation_raw = 20.0
    if recent_scans:
        inflammation_raw += _avg([s.redness_score for s in recent_scans]) * 0.4
    if recent_food:
        inflammation_raw += _avg([f.glycemic_load for f in recent_food]) * 0.2
    if recent_stress:
        inflammation_raw += (_avg([s.stress_level for s in recent_stress]) - 5) * 2
    inflammation = _clamp(100 - inflammation_raw, 10, 100)

    # --- breakoutPressure ("k" in the original, via inverse "A") ---
    breakout_raw = 15.0
    if recent_scans:
        breakout_raw += min(_avg([s.lesion_count for s in recent_scans]) * 3, 40)
    avg_food_risk = _avg([f.overall_risk for f in recent_food]) if recent_food else 0.0
    breakout_raw += avg_food_risk * 0.2
    breakout = _clamp(100 - breakout_raw, 10, 100)

    # --- oilDryBalance ("N" in the original, via "_") ---
    balance_mid = 50.0
    if recent_scans:
        avg_oil = _avg([s.oiliness_score for s in recent_scans])
        avg_dry = _avg([s.dryness_score for s in recent_scans])
        balance_mid = 50 + (avg_oil - avg_dry) * 0.3
    oil_dry_balance = _clamp(100 - abs(balance_mid - 50) * 2, 10, 100)

    # --- healingVelocity ("C" in the original) - uses ALL scans (not just
    # the 7-day window), sorted chronologically, comparing oldest to newest ---
    healing = 60.0
    if len(all_scans) >= 2:
        ordered = sorted(all_scans, key=lambda s: s.captured_at)
        delta = (ordered[-1].lesion_count or 0) - (ordered[0].lesion_count or 0)
        healing = _clamp(60 + delta * 5, 10, 100)

    # --- sensitivityRisk ("P" in the original) ---
    sensitivity = 70.0
    sensitivity -= w * 5
    if skin_type == "sensitive":
        sensitivity -= 20
    sensitivity = _clamp(sensitivity, 10, 100)

    components = {
        "barrierIntegrity": round(barrier),
        "inflammationLoad": round(inflammation),
        "breakoutPressure": round(breakout),
        "oilDryBalance": round(oil_dry_balance),
        "healingVelocity": round(healing),
        "sensitivityRisk": round(sensitivity),
    }

    overall = round(
        components["barrierIntegrity"] * 0.25
        + components["inflammationLoad"] * 0.20
        + components["breakoutPressure"] * 0.20
        + components["oilDryBalance"] * 0.15
        + components["healingVelocity"] * 0.10
        + components["sensitivityRisk"] * 0.10
    )

    if overall >= 80:
        status = HealthIndexStatus.HEALTHY.value
    elif overall >= 65:
        status = HealthIndexStatus.STABLE.value
    elif overall >= 50:
        status = HealthIndexStatus.WATCHLIST.value
    elif overall >= 35:
        status = HealthIndexStatus.AT_RISK.value
    else:
        status = HealthIndexStatus.COMPROMISED.value

    driving_factors: list[str] = []
    if components["barrierIntegrity"] < 60:
        driving_factors.append("Barrier integrity is below optimal range")
    if components["inflammationLoad"] < 60:
        driving_factors.append("Elevated inflammatory markers detected")
    if components["breakoutPressure"] < 60:
        driving_factors.append("Active breakout pressure is elevated")
    if w > 0:
        driving_factors.append(f"{w} product(s) with high irritation potential in routine")
    if recent_sleep and _avg([s.net_sleep_hours for s in recent_sleep]) < 6.5:
        driving_factors.append("Sleep duration averaging below optimal threshold")

    total_points = len(all_scans) + len(all_sleep) + len(all_food) + len(all_stress)
    if total_points < 3:
        data_density = "low"
    elif total_points < 10:
        data_density = "moderate"
    elif total_points < 25:
        data_density = "high"
    else:
        data_density = "very_high"
    validation_status = "insufficient_data" if total_points < 2 else "passed"

    return {
        "calculated_at": now.isoformat(),
        "overall_score": overall,
        "status": status,
        "components": components,
        "driving_factors": driving_factors,
        "data_density": data_density,
        "validation_status": validation_status,
    }
