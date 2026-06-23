"""
TriggerGraph correlation pipeline.

Exact port of `WW` from the recovered v2 bundle, including its Pearson
correlation helper (`nX`) for the sleep/lesion relationship. The cited
studies below are reproduced exactly as they appeared in the deployed
product (real, identifiable dermatology literature - Jovic et al. on sleep
deprivation and acne, Kwon et al. on glycemic load, Adebamowo et al. on
dairy/JAAD, Yosipovitch et al. on stress/JAMA Dermatol), not invented for
this port.
"""
from dataclasses import dataclass
from datetime import datetime


def _pearson(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denom_x = sum((x - mean_x) ** 2 for x in xs) ** 0.5
    denom_y = sum((y - mean_y) ** 2 for y in ys) ** 0.5
    if denom_x == 0 or denom_y == 0:
        return 0.0
    return numerator / (denom_x * denom_y)


def _avg(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


@dataclass
class ScanLite:
    captured_at: datetime
    lesion_count: float


@dataclass
class SleepLite:
    log_date: datetime
    net_sleep_hours: float


@dataclass
class FoodLite:
    log_date: datetime
    glycemic_load: float
    dairy_intake: bool


@dataclass
class StressLite:
    log_date: datetime
    stress_level: float


def compute_trigger_correlations(
    scans: list[ScanLite], sleep_logs: list[SleepLite], food_logs: list[FoodLite], stress_logs: list[StressLite],
) -> list[dict]:
    results: list[dict] = []
    if len(scans) < 2:
        return results

    if len(sleep_logs) >= 3:
        pairs = []
        for sl in sleep_logs:
            nearest = min(scans, key=lambda sc: abs((sc.captured_at - sl.log_date).total_seconds()), default=None)
            if nearest is not None and abs((nearest.captured_at - sl.log_date).total_seconds()) < 172800:
                pairs.append((sl.net_sleep_hours, nearest.lesion_count))
        if len(pairs) >= 2:
            sleep_vals = [p[0] for p in pairs]
            lesion_vals = [p[1] for p in pairs]
            r = _pearson(sleep_vals, lesion_vals)
            results.append({
                "factor": "Poor Sleep Quality", "category": "sleep",
                "correlation_strength": round(-r * 80), "method": "pearson_lagged_48h",
                "confidence": "high" if len(pairs) >= 7 else "moderate",
                "sample_size": len(pairs),
                "evidence": ["Jovic A et al. (2017). Sleep deprivation and acne. International Journal of Molecular Sciences."],
                "notes": f"Average sleep: {_avg(sleep_vals):.1f}h. Average lesions at corresponding time: {_avg(lesion_vals):.1f}.",
            })

    if len(food_logs) >= 3:
        avg_glycemic = _avg([f.glycemic_load for f in food_logs])
        if avg_glycemic > 40:
            results.append({
                "factor": "High Glycemic Diet", "category": "food",
                "correlation_strength": round(min(avg_glycemic * 0.8, 85)), "method": "threshold_heuristic",
                "confidence": "high" if len(food_logs) >= 7 else "moderate",
                "sample_size": len(food_logs),
                "evidence": ["Kwon HH et al. (2012). Low glycemic load diet and acne. Acta Dermato-Venereologica."],
                "notes": "High average glycemic load detected. Elevated insulin signaling may upregulate sebaceous gland activity.",
            })
        dairy_days = sum(1 for f in food_logs if f.dairy_intake)
        if dairy_days > 2:
            results.append({
                "factor": "Dairy Consumption", "category": "food",
                "correlation_strength": round(min((dairy_days / len(food_logs)) * 90, 72)), "method": "threshold_heuristic",
                "confidence": "moderate" if len(food_logs) >= 7 else "low",
                "sample_size": dairy_days,
                "evidence": ["Adebamowo CA et al. (2006). Milk consumption and acne in teenaged boys. Journal of the American Academy of Dermatology."],
                "notes": "Dairy detected on multiple days. IGF-1 from milk may amplify androgen signaling.",
            })

    if len(stress_logs) >= 3:
        avg_stress = _avg([s.stress_level for s in stress_logs])
        if avg_stress > 5:
            results.append({
                "factor": "Elevated Stress", "category": "stress",
                "correlation_strength": round(min(avg_stress * 7, 80)), "method": "threshold_heuristic",
                "confidence": "high" if len(stress_logs) >= 7 else "moderate",
                "sample_size": len(stress_logs),
                "evidence": ["Yosipovitch G et al. (2007). Study of psychological stress, sebum production and acne vulgaris in adolescents. JAMA Dermatology."],
                "notes": f"Average stress level: {avg_stress:.1f}/10. Elevated cortisol may increase sebum production and inflammation.",
            })

    return results
