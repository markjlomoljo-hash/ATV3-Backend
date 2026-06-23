# AcneTrex v3 Backend - Phase 1

Real, server-side auth/persistence/migration foundation for AcneTrex, built from
the recovered v2 bundle as behavioral reference. This is Phase 1 of 3 (see
"What's NOT built yet" below) - it was written by hand in a sandboxed
environment with no internet access and no live Postgres instance, so **it
has not been executed or tested against a real database**. The code follows
correct, current FastAPI/SQLAlchemy 2.0 async patterns throughout, but you
should run the test suite (instructions below) before trusting it in
production, and treat this status note as a real constraint, not boilerplate.

## What's real in this phase

- **Auth**: signup, login, logout, `/auth/me`, forgot/reset password. Argon2id
  password hashing, JWT access tokens backed by real server-side `auth_sessions`
  rows (logout actually revokes a session - a stolen token dies immediately,
  not just on the client).
- **Persistence**: every table in the spec's entity list is modeled in
  `app/db/models/`, with `id` / `created_at` / `updated_at` / `app_version` /
  `schema_version` / `source` on every record via `RecordMixin`.
- **Same-day log merge**: enforced both at the database level (a `UNIQUE`
  constraint on `user_id, log_date, log_type`) and in `log_service.py` (select
  existing -> merge, with an `IntegrityError` fallback for race conditions).
  Sleep/food/activity derived fields (`sleepDebt`, `overallRisk`,
  `breakoutRisk`) use the exact formulas extracted from the recovered v2
  bundle, not reinvented values.
- **Legacy migration**: `POST /v1/auth/migrate` imports `acnetrex_auth_v2`,
  `acnetrex_data_v2`, and `acnetrex_ai_v2` JSON blobs (the frontend reads these
  from localStorage and sends them) into real backend rows, tagged
  `source="localStorage_v2"`, skipping anything that would overwrite an
  existing v3 record.
- **Intelligence status & network participation**: `/intelligence/status`,
  `/intelligence/events`, `/network/status` are real queries over real tables
  - they report zero/empty honestly until Phase 2 services start writing
  `ModelRun` / `IntelligenceEvent` rows, rather than faking activity.
- **Report export**: `GET /v1/reports/export.json` is a real, complete dump of
  a user's stored data today.

## What's NOT built yet (Phase 2/3, contract already defined)

`scans`, `products`, `forecast`, `assistant`, and `evidence` routes exist and
are wired into the router with the correct paths/methods, but currently
return `501 not_implemented_yet` with a clear message - on purpose, instead
of returning fabricated data. Phase 2 fills in:
- `ml/face_pipeline.py` - real image analysis
- `ml/forecast_pipeline.py` - real forecasting with confidence intervals
- `ml/product_pipeline.py` - OCR + ingredient cross-reference
- `services/assistant_service.py` + `services/rag_service.py` - real CutisAI
- `services/evidence_service.py` - real DermVault retrieval/embedding
- PDF report rendering

## Setup

```bash
cp .env.example .env
# edit .env: generate SECRET_KEY, set DATABASE_URL, optionally ANTHROPIC_API_KEY

# Option A: docker compose (Postgres+pgvector, Redis, and the API together)
docker compose up --build

# Option B: run locally against your own Postgres
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
# Postgres must have pgvector: CREATE EXTENSION IF NOT EXISTS vector;
alembic revision --autogenerate -m "initial schema"   # generates the migration from the models in this repo
alembic upgrade head
python -m app.db.seed                                  # seeds model_versions + starter ingredient reference data
uvicorn app.main:app --reload
```

No migration file is checked into this repo - `alembic revision
--autogenerate` against your real database is the correct way to generate
it (it introspects the actual models), and it's something this sandbox could
not do without a live Postgres connection. Open `http://localhost:8000/docs`
for live OpenAPI docs once running.

## Where to deploy

Any host that runs a standard FastAPI/Postgres app works: Render, Railway,
Fly.io, or a Supabase Postgres instance paired with any FastAPI host. None of
this code is tied to a specific provider.

## Testing

```bash
createdb acnetrex_test
DATABASE_URL=postgresql+asyncpg://acnetrex:acnetrex@localhost:5432/acnetrex_test alembic upgrade head
DATABASE_URL=postgresql+asyncpg://acnetrex:acnetrex@localhost:5432/acnetrex_test pytest
```

`app/tests/test_auth.py` covers signup/login/duplicate-signup/wrong-password/
logout-revocation. `app/tests/test_log_merge.py` covers the same-day merge
rule directly, including the server-computed `overallRisk` field, since that
rule is the spec's single most-repeated requirement. These are real
integration tests against a real (disposable) database - they were written
correctly to the best of my ability but **not run**, for the same no-internet
sandbox reason noted at the top.

## Notes on the seeded ingredient data

`app/db/seed.py` ships ~12 starter `IngredientProfile` rows with comedogenic/
irritant/hormonal ratings drawn from commonly-cited dermatology-literature
values (Fulton-scale-style comedogenicity ratings). These are reasonable
starting values, not yet individually linked to an `EvidenceSource` citation
row - wiring each rating to a real citation is exactly the kind of thing
`evidence_source_ids` on `IngredientProfile` exists for, and is Phase 2 scope
alongside the rest of DermVault.

## Frontend integration

The frontend should call this API through a typed client (see the
`AcneTrexClient` example in the original brief) and stop using `localStorage`
for anything except: triggering the one-time `/v1/auth/migrate` import, UI
state, and offline cache. `VITE_API_BASE_URL` should point at wherever you
deploy this service.
