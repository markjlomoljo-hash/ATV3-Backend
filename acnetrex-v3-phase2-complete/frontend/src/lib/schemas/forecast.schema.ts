/**
 * Forecast Zod Schema
 * 
 * Runtime validation for forecast records from the backend.
 * Ensures all Forecast data crossing the service boundary conforms to
 * the expected shape before rendering in components.
 */

import { z } from "zod";

/**
 * Key driver for a forecast (e.g., "Sleep Debt", "Dairy Intake")
 */
export const KeyDriverSchema = z.object({
  factor: z.string(),
}).strict();

/**
 * Complete Forecast record from backend
 */
export const ForecastSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  model_version_id: z.string().uuid(),
  generated_at: z.string().datetime(),
  horizon: z.enum(["7d", "14d", "30d"]),
  current_risk: z.number().min(0).max(100),
  forecasted_risk: z.number().min(0).max(100),
  best_case_risk: z.number().min(0).max(100),
  worst_case_risk: z.number().min(0).max(100),
  confidence_interval_low: z.number().min(0).max(100),
  confidence_interval_high: z.number().min(0).max(100),
  confidence: z.number().min(0).max(1),
  validation_status: z.enum(["passed", "insufficient_data", "low_confidence", "failed"]),
  key_drivers: z.array(KeyDriverSchema).default([]),
  recommendations: z.array(z.string()).default([]),
  estimated_improvement_days: z.number().int().nonnegative().nullable(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  app_version: z.string(),
  schema_version: z.string(),
  source: z.string(),
}).strict();

/**
 * What-If Scenario record
 */
export const WhatIfScenarioSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  base_forecast_id: z.string().uuid().nullable(),
  changed_factors: z.object({
    factors: z.array(z.object({
      factor: z.string(),
      direction: z.enum(["improve", "worsen"]),
      magnitude: z.number().min(0).max(100),
    })),
  }),
  simulated_risk: z.number().min(0).max(100),
  estimated_improvement_days: z.number().int().nonnegative().nullable(),
  explanation: z.string().nullable(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  app_version: z.string(),
  schema_version: z.string(),
  source: z.string(),
}).strict();

export type Forecast = z.infer<typeof ForecastSchema>;
export type KeyDriver = z.infer<typeof KeyDriverSchema>;
export type WhatIfScenario = z.infer<typeof WhatIfScenarioSchema>;
