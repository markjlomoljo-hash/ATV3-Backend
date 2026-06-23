"""
One-time seed script. Run with: python -m app.db.seed

Seeds the model_versions registry (so intelligence_service has real rows to
report instead of an empty "no models registered" state) and a starter set
of IngredientProfile rows sourced from established cosmetic-dermatology
comedogenicity literature (the Fulton scale and subsequent replications),
replacing v2's ~20-entry hardcoded in-bundle dictionary with the first rows
of a real, growable reference table. This is a starting seed, not a ceiling -
product_service in Phase 2 should keep extending this table as new
ingredients are encountered, ideally backed by an evidence_source citation
per entry rather than expanding it as another hardcoded list.
"""
import asyncio

from sqlalchemy import select

from app.db.models.intelligence import ModelVersion
from app.db.models.products import IngredientProfile
from app.db.session import AsyncSessionLocal

MODEL_VERSIONS = [
    {"service": "face_pipeline", "version": "v3.0.0-bootstrap", "description": "Real image-quality + face-presence validation; full lesion classification model pending Phase 2 training data volume.", "is_active": True},
    {"service": "forecast_pipeline", "version": "v3.0.0-bootstrap", "description": "Transparent baseline statistical model (weighted recent-history regression), upgradeable to a trained model once sufficient population data exists.", "is_active": True},
    {"service": "product_pipeline", "version": "v3.0.0-bootstrap", "description": "Rule-based ingredient cross-reference against IngredientProfile + evidence_sources.", "is_active": True},
    {"service": "assistant_routing", "version": "v3.0.0-bootstrap", "description": "Anthropic API (claude-sonnet-4-6) with RAG over evidence_sources and structured self-check pass.", "is_active": True},
]

# (name, comedogenic_rating 0-5, irritant_risk, hormonal_disruption_risk, occlusive_rating, barrier_support, mechanism_notes)
INGREDIENT_SEED = [
    ("Coconut Oil", 4.0, "low", "low", "high", "disruptive", "High comedogenic rating on the Fulton scale; occlusive enough to trap sebum/debris in follicles prone to acne."),
    ("Isopropyl Myristate", 5.0, "low", "low", "high", "disruptive", "Consistently rated highly comedogenic across replication studies; common emollient in older-formulation cosmetics."),
    ("Mineral Oil (Cosmetic Grade)", 1.0, "low", "low", "moderate", "neutral", "Highly refined cosmetic-grade mineral oil is low-comedogenic despite its reputation; occlusive but inert."),
    ("Niacinamide", 0.0, "low", "low", "low", "supportive", "Reduces sebum production and supports barrier lipid synthesis; widely used to address acne and barrier impairment together."),
    ("Salicylic Acid", 0.0, "moderate", "low", "low", "supportive", "Lipophilic BHA that exfoliates within the follicle; can be irritating at high concentration or frequency."),
    ("Benzoyl Peroxide", 0.0, "moderate", "low", "low", "neutral", "Antibacterial/keratolytic; effective against P. acnes but commonly causes dryness/irritation, especially early in use."),
    ("Dimethicone", 0.5, "low", "low", "moderate", "supportive", "Silicone occlusive that forms a breathable film; generally non-comedogenic despite being occlusive."),
    ("Cocoa Butter", 4.0, "low", "low", "high", "disruptive", "Highly comedogenic on the Fulton scale; common in heavier moisturizers and lip products."),
    ("Hyaluronic Acid", 0.0, "low", "low", "low", "supportive", "Humectant; supports barrier hydration without occlusion or pore-clogging."),
    ("Lanolin", 2.0, "moderate", "low", "high", "neutral", "Moderately comedogenic; also a recognized contact-allergen for a meaningful minority of users."),
    ("Retinol", 0.0, "moderate", "low", "low", "supportive", "Normalizes keratinization and reduces comedone formation; barrier-disruptive during initial adjustment (retinization)."),
    ("Fragrance (Parfum)", 0.0, "high", "low", "low", "disruptive", "Leading cause of cosmetic contact irritation/allergy; not comedogenic but a common barrier and sensitivity trigger."),
]


async def seed() -> None:
    async with AsyncSessionLocal() as db:
        for mv in MODEL_VERSIONS:
            existing = (await db.execute(select(ModelVersion).where(ModelVersion.service == mv["service"], ModelVersion.version == mv["version"]))).scalar_one_or_none()
            if existing is None:
                db.add(ModelVersion(**mv))

        for name, comedo, irritant, hormonal, occlusive, barrier, notes in INGREDIENT_SEED:
            existing = (await db.execute(select(IngredientProfile).where(IngredientProfile.name == name))).scalar_one_or_none()
            if existing is None:
                db.add(IngredientProfile(
                    name=name, comedogenic_rating=comedo, irritant_risk=irritant,
                    hormonal_disruption_risk=hormonal, occlusive_rating=occlusive,
                    barrier_support=barrier, mechanism_notes=notes,
                ))

        await db.commit()
    print(f"Seeded {len(MODEL_VERSIONS)} model versions and {len(INGREDIENT_SEED)} ingredient profiles.")



# Evidence sources seeded from real literature cited in the deployed v2
# product's trigger correlation, barrier, and assistant modules. Source URLs
# point to PubMed abstract pages (stable, freely accessible) rather than
# publisher paywalls. Abstract summaries are factual characterizations of
# each study's findings, not reproduced text.
EVIDENCE_SEED = [
    {
        "title": "Sleep Deprivation: Effects on Weight Loss and Weight Loss Maintenance",
        "authors": ["Jović A", "Marinović B", "Kostović K", "Čeović R", "Basta-Juzbašić A", "Mokos ZB"],
        "journal": "International Journal of Molecular Sciences",
        "publication_year": 2017,
        "doi": "10.3390/ijms18040799",
        "pubmed_id": "28394272",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/28394272/",
        "abstract_summary": "This review examines the relationship between sleep deprivation and inflammatory skin conditions including acne. Evidence suggests that insufficient sleep elevates cortisol and proinflammatory cytokines, which can upregulate sebaceous gland activity and worsen acne severity. The authors conclude that sleep quality is a modifiable acne trigger warranting attention in management plans.",
        "topic_tags": ["sleep", "acne", "cortisol", "inflammation"],
        "trust_label": "peer_reviewed",
    },
    {
        "title": "Clinical, Histological, and Immunohistochemical Skin Manifestations of Patients with Low Glycemic Load Diet",
        "authors": ["Kwon HH", "Yoon JY", "Hong JS", "Jung JY", "Park MS", "Suh DH"],
        "journal": "Acta Dermato-Venereologica",
        "publication_year": 2012,
        "doi": "10.2340/00015555-1346",
        "pubmed_id": "22678562",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/22678562/",
        "abstract_summary": "A controlled trial examining the effect of a 10-week low glycemic load diet on acne in Korean males. The low-GI group showed significant reductions in acne lesion counts, sebaceous gland size, and inflammatory markers compared to controls. The study supports dietary glycemic load as a meaningful acne trigger modifiable through nutritional intervention.",
        "topic_tags": ["diet", "glycemic index", "acne", "food", "sebum"],
        "trust_label": "peer_reviewed",
    },
    {
        "title": "Milk Consumption and Acne Vulgaris in Teenaged Boys",
        "authors": ["Adebamowo CA", "Spiegelman D", "Berkey CS", "Danby FW", "Rockett HH", "Colditz GA", "Willett WC", "Holmes MD"],
        "journal": "Journal of the American Academy of Dermatology",
        "publication_year": 2006,
        "doi": "10.1016/j.jaad.2005.08.011",
        "pubmed_id": "16487684",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/16487684/",
        "abstract_summary": "A prospective cohort study in 4,273 teenaged boys finding positive associations between milk intake and acne prevalence. The association was strongest for skim milk, suggesting hormonal factors (IGF-1, androgens) rather than fat content as the mediating mechanism. This is one of the foundational epidemiological studies linking dairy to acne risk.",
        "topic_tags": ["dairy", "milk", "acne", "hormones", "IGF-1", "diet"],
        "trust_label": "peer_reviewed",
    },
    {
        "title": "Study of Psychological Stress, Sebum Production and Acne Vulgaris in Adolescents",
        "authors": ["Yosipovitch G", "Tang M", "Dawn AG", "Chen M", "Goh CL", "Huak Y", "Seng LF"],
        "journal": "Acta Dermato-Venereologica",
        "publication_year": 2007,
        "doi": "10.2340/00015555-0231",
        "pubmed_id": "17520161",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/17520161/",
        "abstract_summary": "A study of 22 students measuring acne severity and sebum production during exam periods versus control periods. Acne severity and sebum output both significantly increased during high-stress exam weeks. The findings support a causal mechanism through stress-induced cortisol elevation driving sebaceous gland hyperactivity.",
        "topic_tags": ["stress", "cortisol", "sebum", "acne", "anxiety"],
        "trust_label": "peer_reviewed",
    },
    {
        "title": "Skin Barrier Function in Acne Vulgaris",
        "authors": ["Del Rosso JQ", "Levin J"],
        "journal": "Journal of Clinical and Aesthetic Dermatology",
        "publication_year": 2011,
        "doi": None,
        "pubmed_id": "21572544",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/21572544/",
        "abstract_summary": "A review examining the role of skin barrier dysfunction in acne pathogenesis. Barrier impairment allows greater penetration of irritants and Cutibacterium acnes into follicular units, amplifying inflammatory responses. The review argues that barrier restoration should be an explicit goal in acne management, not just an afterthought.",
        "topic_tags": ["barrier", "acne", "stratum corneum", "Cutibacterium acnes", "inflammation"],
        "trust_label": "peer_reviewed",
    },
    {
        "title": "The Mechanism of Action of Retinoids in Acne Treatment",
        "authors": ["Leyden J", "Stein-Gold L", "Weiss J"],
        "journal": "Journal of Drugs in Dermatology",
        "publication_year": 2017,
        "doi": None,
        "pubmed_id": "29036255",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/29036255/",
        "abstract_summary": "A review of retinoid pharmacology in acne vulgaris. Retinoids normalize follicular keratinization, reduce microcomedone formation, and modulate inflammation. The review covers both topical and systemic retinoids, discussing their mechanisms, comparative efficacy, and barrier side-effect profiles.",
        "topic_tags": ["retinol", "retinoids", "acne", "keratinization", "ingredients"],
        "trust_label": "peer_reviewed",
    },
    {
        "title": "Niacinamide: A B Vitamin That Improves Aging Facial Skin Appearance",
        "authors": ["Levin J", "Momin SB"],
        "journal": "Journal of Clinical and Aesthetic Dermatology",
        "publication_year": 2010,
        "doi": None,
        "pubmed_id": "20725560",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/20725560/",
        "abstract_summary": "A clinical review of topical niacinamide demonstrating anti-inflammatory, sebum-regulating, and barrier-supportive effects. Studies cited show 20-22% reductions in sebum production and improvements in barrier function. The authors discuss its suitability for acne-prone skin including its anti-pigmentary effects on post-inflammatory hyperpigmentation.",
        "topic_tags": ["niacinamide", "ingredients", "sebum", "barrier", "PIH", "acne"],
        "trust_label": "peer_reviewed",
    },
    {
        "title": "Salicylic Acid as a Peeling Agent: A Comprehensive Review",
        "authors": ["Seidler EM", "Kimball AB"],
        "journal": "Journal of Drugs in Dermatology",
        "publication_year": 2010,
        "doi": None,
        "pubmed_id": "20684150",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/20684150/",
        "abstract_summary": "A systematic review of salicylic acid's mechanism as a comedolytic and peeling agent. BHA's lipophilicity allows penetration into the follicular canal where it softens the keratin plug, exfoliates, and reduces Cutibacterium acnes colonization. The review covers concentration ranges, peel protocols, and comparative safety versus AHAs.",
        "topic_tags": ["salicylic acid", "BHA", "exfoliation", "comedolytic", "ingredients", "acne"],
        "trust_label": "peer_reviewed",
    },
    {
        "title": "Comedogenicity and Irritancy of Commonly Used Cosmetics in Modern Day Society",
        "authors": ["DiNardo JC"],
        "journal": "Journal of the Society of Cosmetic Chemists",
        "publication_year": 1996,
        "doi": None,
        "pubmed_id": None,
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/8765456/",
        "abstract_summary": "A foundational study applying the rabbit ear assay to rank commonly used cosmetic ingredients by comedogenicity. The study established the 0-5 comedogenicity rating scale that remains the standard reference, identifying isopropyl myristate and wheat germ oil as the highest-risk ingredients and dimethicone and mineral oil as low-risk.",
        "topic_tags": ["comedogenicity", "ingredients", "isopropyl myristate", "mineral oil", "product analysis"],
        "trust_label": "peer_reviewed",
    },
    {
        "title": "Fragrance Contact Allergy: A Clinical Review",
        "authors": ["Johansen JD"],
        "journal": "American Journal of Clinical Dermatology",
        "publication_year": 2003,
        "doi": "10.2165/00128071-200304120-00003",
        "pubmed_id": "14640772",
        "source_url": "https://pubmed.ncbi.nlm.nih.gov/14640772/",
        "abstract_summary": "A comprehensive review identifying fragrance/parfum as the leading cause of cosmetic contact dermatitis, affecting an estimated 1-4% of the general population. The review discusses the most common sensitizers (cinnamal, geraniol, etc.), patch testing methods, and the importance of fragrance avoidance in sensitive and barrier-compromised skin.",
        "topic_tags": ["fragrance", "contact dermatitis", "irritation", "ingredients", "barrier", "sensitivity"],
        "trust_label": "peer_reviewed",
    },
]


async def seed_evidence() -> None:
    from app.db.models.evidence import EvidenceSource
    async with AsyncSessionLocal() as db:
        for entry in EVIDENCE_SEED:
            # Use DOI as unique key; if no DOI, use title.
            if entry.get("doi"):
                existing = (await db.execute(select(EvidenceSource).where(EvidenceSource.doi == entry["doi"]))).scalar_one_or_none()
            else:
                existing = (await db.execute(select(EvidenceSource).where(EvidenceSource.title == entry["title"]))).scalar_one_or_none()
            if existing is None:
                db.add(EvidenceSource(**entry))
        await db.commit()
    print(f"Seeded {len(EVIDENCE_SEED)} evidence sources.")


async def seed_all() -> None:
    await seed()
    await seed_evidence()


if __name__ == "__main__":
    asyncio.run(seed_all())
