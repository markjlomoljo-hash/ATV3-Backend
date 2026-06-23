# AcneTrex v3 Upgrade: Architecture Plan

**Author**: Manus AI

## 1. Introduction

This document outlines the architecture plan for upgrading the existing AcneTrex website to AcneTrex v3. The primary objective is to transform AcneTrex into a real, production-grade, mobile-first skin intelligence platform. This involves implementing durable persistence, robust authentication, internet-backed retrieval, real AI/ML services with learning loops, and strictly adhering to the "Zero-Fabrication Contract" to eliminate any fake logic. This plan synthesizes requirements from the `acnetrex-v3-upgrade` skill, the user's detailed prompt, and an audit of the existing `ATV3-Backend` repository.

## 2. Core Principles

The upgrade will be guided by two fundamental contracts:

### 2.1. Zero-Fabrication Contract

No production path in the AcneTrex codebase may contain:

*   `Math.random()` used to generate displayed scores, percentages, or risk levels.
*   Hardcoded numeric values, status strings, participant counts, or trend indicators not derived from real entity records or parsed InvokeLLM responses.
*   Arrays of mock, sample, demo, or dummy data.
*   Placeholder implementations that render UI cards but do not execute a real inference or persistence pipeline.
*   Simplified AI/ML logic replacing multi-step engines with static templates or single generic model calls.
*   Decorative status badges, model maturity tiers, or research-network statistics not computed from actual entity queries and consent records.
*   Silent failures that return `undefined`, `null`, or default values without emitting an error state.
*   Duplicate same-day log records when the intended behavior is to update the existing record.
*   Client-side-only authentication patterns used as the production auth system.
*   Uncontrolled self-modifying models.
*   Contradictory state paths that can produce inconsistent outcomes depending on race timing.

Where real data does not yet exist, components must render a shared `EmptyState` or `InsufficientDataState` component. Invented values must never be substituted for missing real values.

### 2.2. Intelligence Engine Execution Contract

Every AI module (FaceAtlas, CutisAI, Forecasting, FormulaLens, DermVault) must function as a real operational engine that materially changes application behavior, persists outputs, emits telemetry, and feeds downstream systems. This contract mandates a 10-point standard:

1.  **Real Inputs**: From user data, logs, scans, products, evidence, weather/context, prior outputs, consent state, and feedback.
2.  **Explicit Pipeline**: Acquisition → Preprocessing → Validation → Inference/Reasoning → Post-processing → Confidence Generation → Acceptance Validation → Persistence → Telemetry Emission → UI Consumption.
3.  **Persisted Outputs**: With source context (engine type, input references, model/algorithm version, timestamp, schema version, confidence, validation status, rationale, user ownership, downstream consumers, and evidence used).
4.  **Downstream Effect**: On CutisAI, forecasts, TriggerGraph, CHI, reports, task prioritization, evidence display, or model readiness.
5.  **Validation Gate**: Input sufficiency, input quality, evidence alignment, safety checks, consistency checks, confidence threshold, and outlier checks before display.
6.  **Learning Loop**: Consumes feedback for calibration, reliability tracking, trend evaluation, confidence adjustment, or model assessment, with no uncontrolled self-modifying behavior.
7.  **Orchestration**: Via Intelligence Core, tracking execution state, readiness, failures, recoveries, model versions, telemetry, validation status, and milestone progression.
8.  **Defined Failure Behavior**: Graceful degradation if data is insufficient, confidence is low, retrieval fails, validation fails, or the model cannot support a conclusion.
9.  **No Placeholder Disguised as Production**: No mock logic, fake metrics, random percentages, simulated learning, dummy participation, or decorative indicators.
10. **Acceptance Standard**: Real inputs, explicit processing, persisted outputs, validation, telemetry, downstream effect, failure modes, surfaced confidence, no placeholder behavior.

## 3. Current State Overview

The `ATV3-Backend` repository provides a solid foundation for the upgrade. Key observations from the audit include:

*   **Backend Framework**: FastAPI with SQLAlchemy ORM, designed for PostgreSQL.
*   **Authentication**: Basic signup, login, logout, and password reset functionalities are implemented in `auth_service.py` and `auth.py` routes. Server-side sessions are managed via `AuthSession` model.
*   **Persistence**: Core data models are defined in `app/db/models/`. The `RecordMixin` ensures consistent metadata for all records. The `AuditLog` model exists but is currently only used for authentication-related events.
*   **Same-Day Log Merge**: The `log_service.py` correctly implements the same-day log merge logic with a `UNIQUE` constraint and `IntegrityError` fallback, covering daily log types defined in `core/constants.py`.
*   **Migration**: A `POST /v1/auth/migrate` endpoint and `migration_service.py` are in place for a one-time import of legacy `localStorage` data.
*   **Intelligence Core**: `intelligence_service.py` provides a basic status system that honestly reports AI/ML activity based on `ModelRun` and `IntelligenceEvent` records. It correctly indicates 
zero activity until Phase 2 services are implemented, adhering to the Zero-Fabrication Contract.
*   **AI/ML Pipelines (Phase 2/3 Readiness)**: Placeholder implementations exist for `scans`, `products`, `forecast`, `assistant`, and `evidence` routes, returning `501 not_implemented_yet`. The `ml` directory contains `forecast_pipeline.py`, `health_index_pipeline.py`, `product_pipeline.py`, and `trigger_pipeline.py`, indicating the structure for future AI/ML integration. `scan_service.py` handles image storage to S3 and sets `validation_status="pending_analysis"`.
*   **Validation**: `validation_service.py` centralizes validation logic for image metrics, forecast data density, product analysis, and assistant responses, ensuring consistent application of `ValidationStatus`.
*   **Frontend Integration**: The `frontend/src/lib/api/client.ts` shows API client definitions for various services, indicating the frontend is structured to consume these backend APIs. However, there are no existing `src/lib/schemas` or `src/components/shared` directories in the frontend, which will need to be created.

## 4. Proposed Architecture and Implementation Plan

This upgrade will proceed in three distinct phases, building upon the existing backend structure and adhering to the defined contracts.

### 4.1. Data Model and Persistence Strategy

*   **Database**: Continue using PostgreSQL with SQLAlchemy ORM. Leverage `RecordMixin` for all new models to ensure `created_at`, `updated_at`, `app_version`, and `schema_version` are consistently tracked.
*   **Audit Logs**: Extend the `AuditLog` mechanism to cover all writes to health-data entities as mandated by the Zero-Fabrication Contract. This will involve modifying relevant service functions (e.g., `log_service.py`, `scan_service.py`, `product_service.py`, `assistant_service.py`, `forecast_service.py`) to emit `AuditLog` records after successful operations.
*   **Version Control**: Ensure all persisted outputs from AI/ML models include `model_version` and `source_context` for traceability and learning loops.
*   **Same-Day Log Merge**: The existing implementation in `log_service.py` is robust and will be maintained.

### 4.2. AI/ML Routing and Services

*   **Intelligence Core**: The `intelligence_service.py` will be the central orchestrator for all AI/ML activities, tracking execution state, readiness, failures, and model versions. All AI modules will emit structured `IntelligenceEvent` records.
*   **InvokeLLM Integration**: Adhere strictly to the `InvokeLLM Operational Constraint Matrix`:
    *   Use `gemini_3_f` for internet-augmented calls, `claude_sonnet_4_6` for high-complexity reasoning.
    *   Vision calls (with `file_urls`) must not use `add_context_from_internet: true`.
    *   `response_json_schema.root` must always be `{ type: "object" }`.
    *   Implement mandatory timeout and retry logic (10s–45s) using `invokeWithRetry`.
*   **Prompt Management**: Implement `src/lib/ai/promptBuilder.ts` to manage token budgets and context windows for all InvokeLLM prompts, ensuring truncation of lower-priority sections when necessary.

### 4.3. Authentication and Migration

*   **Authentication**: The existing server-side authentication with `AuthSession` and JWTs is suitable. Ensure `remember_me` functionality and session revocation are fully functional.
*   **Legacy Migration**: The `POST /v1/auth/migrate` endpoint and `migration_service.py` will be used for a one-time import of legacy `localStorage` data. This process must be robust, handling partial migrations and avoiding data overwrites.

### 4.4. Validation Strategy

*   **Runtime Schema Validation (Zod)**: Introduce Zod schemas for all frontend data validation. All schemas will reside in `src/lib/schemas/<entity>.schema.ts`. Service functions and custom hooks will use `z.safeParse()` to validate LLM responses and entity records, setting an error state on failure and never rendering partial data.
*   **Centralized Validation**: Continue to leverage `validation_service.py` in the backend to enforce consistent validation rules across all AI/ML pipelines, ensuring no fabricated certainty reaches the user.

### 4.5. Frontend Architecture

*   **Mobile-First Design**: Ensure all UI components are responsive and optimized for mobile devices, adhering to the `SYSTEM REQUIREMENTS` for a polished, touch-friendly, and accessible experience.
*   **Shared Components**: Create `src/components/shared/EmptyState.tsx` and `src/components/shared/InsufficientDataState.tsx` to handle empty or insufficient data scenarios, as mandated by the Zero-Fabrication Contract. Define minimum thresholds in `src/lib/constants/dataThresholds.ts`.
*   **Progressive Disclosure**: Implement UI patterns that show summary information first, with details available on demand.
*   **Race Condition Protection**: Apply the `useRef`-based guard pattern to all form submission handlers and AI-triggering actions to prevent double-submission issues in concurrent mode.

## 5. Implementation Phases

### Phase 1: Foundation (Backend & Frontend)

*   **Zod Schemas**: Create `src/lib/schemas/<entity>.schema.ts` for all relevant entities in the frontend.
*   **Shared State Components**: Implement `EmptyState.tsx` and `InsufficientDataState.tsx` in `src/components/shared/`.
*   **Data Thresholds**: Define `FORECAST_MIN_DAYS`, `TRIGGER_GRAPH_MIN_DAYS`, `SKIN_TWIN_MIN_SCANS`, `BARRIER_MIN_DAYS`, `CHI_MIN_LOGS` in `src/lib/constants/dataThresholds.ts`.
*   **Audit Log Enhancement**: Modify backend services to emit `AuditLog` records for all health-data entity writes.
*   **Auth Layer Hardening**: Review and enhance the existing authentication layer for robustness and security, ensuring proper session management and token handling.
*   **Migration Flow**: Implement the frontend logic to trigger the `POST /v1/auth/migrate` endpoint and handle the `LegacyMigrationResult`.

### Phase 2: Intelligence Engines (Backend)

*   **FaceAtlas**: Implement `ml/face_pipeline.py` for real image analysis, including image quality validation, face detection, lesion classification, and estimation of skin attributes. Integrate with `scan_service.py` to process `pending_analysis` scans.
*   **CutisAI**: Implement `assistant_service.py` to integrate with InvokeLLM for real assistant capabilities, including context assembly, evidence retrieval, self-check passes, and persistence of conversations and messages.
*   **Forecasting Engine**: Enhance `ml/forecast_pipeline.py` to consume historical logs, scans, and product data to generate future horizons, simulate scenarios, and explain contributing factors. Integrate with `forecast_service.py`.
*   **FormulaLens**: Implement `ml/product_pipeline.py` for product and ingredient risk analysis, matching ingredients against `IngredientProfile` and calculating risk scores. Integrate with `product_service.py`.
*   **DermVault**: Implement `evidence_service.py` for real evidence retrieval, indexing metadata, searching by query, and providing source trust labels.

### Phase 3: Broken-Flow Repair and Refinement (Frontend & Backend)

*   **Same-Day Merge UI**: Ensure the frontend correctly handles same-day log entries by updating existing records instead of creating duplicates.
*   **Onboarding Gates**: Implement robust onboarding gates and ensure smooth user progression through the onboarding flow.
*   **Route Redirects**: Verify and fix any broken route redirects, ensuring a seamless user experience.
*   **Race-Condition Guards**: Implement `useRef`-based guards for all critical user actions in the frontend to prevent race conditions.
*   **Empty/Insufficient Data States**: Integrate the `EmptyState` and `InsufficientDataState` components across the frontend where data is missing or insufficient for analysis.
*   **Comprehensive Testing**: Conduct thorough end-to-end testing to ensure all new features and upgrades function as expected and adhere to the Zero-Fabrication Contract.

## 6. References

[1] `acnetrex-v3-upgrade` skill: `/home/ubuntu/skills/acnetrex-v3-upgrade/SKILL.md`
[2] User provided prompt: `/home/ubuntu/upload/Pasted_content_04.txt`
[3] `ATV3-Backend` repository: `https://github.com/markjlomoljo-hash/ATV3-Backend`
[4] `architecture.md` reference: `/home/ubuntu/skills/acnetrex-v3-upgrade/references/architecture.md`
[5] `ai_ml_guidelines.md` reference: `/home/ubuntu/skills/acnetrex-v3-upgrade/references/ai_ml_guidelines.md`
