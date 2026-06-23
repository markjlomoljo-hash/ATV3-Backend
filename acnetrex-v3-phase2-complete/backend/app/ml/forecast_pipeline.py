"""
ClearPath Forecast + What-If Simulator pipeline.

Exact port of `h5` (forecast) and `XW` (what-if) from the recovered v2
bundle. The horizon-dampening factor, clamp ranges, and recommendation
trigger logic are preserved as-is so forecasts remain interpretable in the
same terms the original product used, while now running on real persisted
history instead of a mock data layer.
"""
import math
from dataclasses import dataclass
from datetime import datetime


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@dataclass
class LatestScan:
    lesion_count: float = 0.0
    redness_score: float = 0.0
    oiliness_score: float = 0.0


def compute_forecast(
    latest_scan: LatestScan | None,
    trigger_correlations: list[dict],
    total_history_points: int,
    horizon_days: int = 7,
) -> dict:
    data_density = (
        "low" if total_history_points < 5 else
        "moderate" if total_history_points < 15 else
        "high" if total_history_points < 30 else
        "very_high"
    )

    current_risk = 40.0
    if latest_scan is not None:
        current_risk = round(
            (latest_scan.lesion_count or 0) * 2
            + (latest_scan.redness_score or 0) * 0.3
            + (latest_scan.oiliness_score or 0) * 0.2
        )
        current_risk = _clamp(current_risk, 5, 95)

    strong_triggers = [c for c in trigger_correlations if c["correlation_strength"] > 60]
    trigger_pressure = sum(c["correlation_strength"] * 0.05 for c in strong_triggers)

    horizon_dampening = 1 - math.log10(max(horizon_days, 1)) * 0.1
    forecasted_risk = _clamp(round((current_risk + trigger_pressure) * horizon_dampening), 5, 95)
    best_case = _clamp(round(forecasted_risk * 0.55), 5, 90)
    worst_case = _clamp(round(forecasted_risk * 1.4), 5, 95)

    key_drivers = [c["factor"] for c in strong_triggers[:3]]
    if not key_drivers:
        key_drivers = ["Baseline skin condition"]

    recommendations: list[str] = []
    factor_names = " ".join(c["factor"] for c in strong_triggers)
    if "Sleep" in factor_names:
        recommendations.append("Prioritize 7.5-8h of consistent sleep this week")
    if "Glycemic" in factor_names or "Dairy" in factor_names:
        recommendations.append("Reduce high-glycemic and dairy foods for the next 7 days")
    if "Stress" in factor_names:
        recommendations.append("Implement a stress reduction activity daily")
    if not recommendations:
        recommendations.append("Maintain current routine and continue logging for improved accuracy")

    estimated_improvement_days = round(horizon_days * (forecasted_risk / 100) * 1.2)

    return {
        "generated_at": datetime.utcnow().isoformat(),
        "horizon": f"{horizon_days}d",
        "current_risk": current_risk,
        "forecasted_risk": forecasted_risk,
        "best_case_risk": best_case,
        "worst_case_risk": worst_case,
        "confidence_interval_low": best_case,
        "confidence_interval_high": worst_case,
        "confidence": data_density,
        "validation_status": "insufficient_data" if total_history_points < 3 else "passed",
        "key_drivers": key_drivers,
        "recommendations": recommendations,
        "estimated_improvement_days": estimated_improvement_days,
    }


def compute_what_if(baseline_risk: float, changed_factors: list[dict]) -> dict:
    """changed_factors: [{"factor": str, "direction": "improve"|"worsen", "magnitude": float}]"""
    impacts = []
    for cf in changed_factors:
        impact = -round(cf["magnitude"] * 0.3) if cf["direction"] == "improve" else round(cf["magnitude"] * 0.25)
        impacts.append({
            "factor": cf["factor"],
            "change": f"Improve {cf['factor']}" if cf["direction"] == "improve" else f"Worsen {cf['factor']}",
            "impact_estimate": impact,
        })

    total_impact = sum(i["impact_estimate"] for i in impacts)
    simulated_risk = _clamp(baseline_risk + total_impact, 5, 95)
    delta = baseline_risk - simulated_risk

    improved_factors = [cf["factor"] for cf in changed_factors if cf["direction"] == "improve"]
    if delta > 0:
        explanation = (
            f"By addressing {', '.join(improved_factors)}, your estimated breakout risk could decrease "
            f"by ~{abs(round(delta))} points. This is based on your personal trigger correlation data."
        )
    else:
        explanation = "The selected changes are estimated to have a neutral or mildly negative impact on your skin condition based on your logged data."

    return {
        "changed_factors": impacts,
        "baseline_risk": baseline_risk,
        "simulated_risk": simulated_risk,
        "estimated_improvement_days": round(abs(delta) * 0.7),
        "confidence": "moderate",
        "explanation": explanation,
    }
