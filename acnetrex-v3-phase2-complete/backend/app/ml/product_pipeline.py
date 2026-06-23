"""
FormulaLens ingredient analysis pipeline.

`match_ingredients` replaces v2's `QW` (which substring-matched against a
~20-entry dictionary baked into the JS bundle) with a real query against the
`ingredient_profiles` table - the matching logic (substring match against
ingredient name/aliases) is preserved, but the data source is now a real,
growable, queryable table instead of a fixed list. `score_product` is an
exact port of `JW`'s risk-scoring math.
"""
from dataclasses import dataclass


@dataclass
class MatchedIngredient:
    name: str
    comedogenic_rating: float
    irritant_risk: str          # low|moderate|high
    barrier_support: str        # supportive|neutral|disruptive
    acne_association: str       # none|possible|likely|high
    profile_id: str | None = None


def match_ingredients(raw_text: str, ingredient_profiles: list[dict]) -> list[MatchedIngredient]:
    """ingredient_profiles: [{"id": str, "name": str, "aliases": list[str],
    "comedogenic_rating": float, "irritant_risk": str, "barrier_support": str}]
    Acne association is derived from comedogenic_rating (>=4 -> high,
    >=2 -> possible, else none) since IngredientProfile doesn't store it as
    a separate field - this mirrors how the original dictionary's
    `acneAssociation` values lined up with its `comedogenic` ratings."""
    text_lower = raw_text.lower()
    matched: list[MatchedIngredient] = []
    for profile in ingredient_profiles:
        names_to_check = [profile["name"]] + (profile.get("aliases") or [])
        if any(n.lower() in text_lower for n in names_to_check):
            comedo = profile.get("comedogenic_rating") or 0
            association = "high" if comedo >= 4 else "possible" if comedo >= 2 else "none"
            matched.append(MatchedIngredient(
                name=profile["name"],
                comedogenic_rating=comedo,
                irritant_risk=profile.get("irritant_risk") or "low",
                barrier_support=profile.get("barrier_support") or "neutral",
                acne_association=association,
                profile_id=profile.get("id"),
            ))
    return matched


def score_product(matched: list[MatchedIngredient]) -> dict:
    if not matched:
        return {
            "overall_risk": 50, "comedogenic_score": 2.0, "irritation_risk": 30,
            "barrier_support_score": 50, "acne_trigger_likelihood": 30,
            "conclusion": "Insufficient ingredient data for analysis. Enter more ingredients for a detailed assessment.",
            "confidence_level": "low",
        }

    avg_comedo = min(5, sum(m.comedogenic_rating for m in matched) / len(matched))
    irritation_risk = round((sum(1 for m in matched if m.irritant_risk == "high") / len(matched)) * 100)
    negative_barrier = sum(1 for m in matched if m.barrier_support == "disruptive")
    positive_barrier = sum(1 for m in matched if m.barrier_support == "supportive")
    barrier_support_score = max(0, min(100, 50 + (positive_barrier - negative_barrier) * 15))

    high_assoc = sum(1 for m in matched if m.acne_association in ("likely", "high"))
    acne_trigger_likelihood = round(min((high_assoc / len(matched)) * 100 + avg_comedo * 10, 100))

    overall_risk = round(avg_comedo / 5 * 35 + irritation_risk * 0.3 + acne_trigger_likelihood * 0.35)
    overall_risk = max(0, min(100, overall_risk))

    flagged = [m for m in matched if m.comedogenic_rating >= 4 or m.acne_association == "high"]
    if flagged:
        conclusion = (
            f"This formula contains {', '.join(m.name for m in flagged)}, which have elevated comedogenic "
            f"or acne-triggering profiles. Exercise caution if acne-prone."
        )
    elif irritation_risk > 50:
        conclusion = "Moderate irritation potential detected. Monitor for barrier sensitivity, particularly around active lesions."
    elif barrier_support_score > 65:
        conclusion = "This product appears barrier-supportive with low comedogenic and irritation risk. Generally suitable for acne-prone skin."
    else:
        conclusion = "Moderate overall risk profile. Compatible with most acne-prone skin types but monitor for individual reactions."

    confidence_level = "high" if len(matched) >= 5 else "moderate" if len(matched) >= 2 else "low"

    return {
        "overall_risk": overall_risk,
        "comedogenic_score": round(avg_comedo, 1),
        "irritation_risk": irritation_risk,
        "barrier_support_score": barrier_support_score,
        "acne_trigger_likelihood": acne_trigger_likelihood,
        "conclusion": conclusion,
        "confidence_level": confidence_level,
    }
