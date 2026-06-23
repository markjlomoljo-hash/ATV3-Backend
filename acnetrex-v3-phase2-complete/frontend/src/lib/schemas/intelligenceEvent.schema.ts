/**
 * IntelligenceEvent Zod Schema
 * 
 * Runtime validation for intelligence event records from the backend.
 * Ensures all event data crossing the service boundary conforms to
 * the expected shape before rendering in components.
 */

import { z } from "zod";

/**
 * Complete IntelligenceEvent record from backend
 */
export const IntelligenceEventSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  event_type: z.string(),
  event_detail: z.record(z.unknown()).default({}),
  occurred_at: z.string().datetime(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  app_version: z.string(),
  schema_version: z.string(),
  source: z.string(),
}).strict();

/**
 * Intelligence status response from backend
 */
export const IntelligenceStatusSchema = z.object({
  tier: z.enum(["bootstrap", "developing", "calibrated", "advanced"]),
  total_inferences: z.number().int().nonnegative(),
  active_models: z.number().int().nonnegative(),
  events_last_24h: z.number().int().nonnegative(),
  last_activity_at: z.string().datetime().nullable(),
  is_idle: z.boolean(),
}).strict();

/**
 * Model version record
 */
export const ModelVersionSchema = z.object({
  id: z.string().uuid(),
  service: z.string(),
  version: z.string(),
  is_active: z.boolean(),
  created_at: z.string().datetime(),
}).strict();

export type IntelligenceEvent = z.infer<typeof IntelligenceEventSchema>;
export type IntelligenceStatus = z.infer<typeof IntelligenceStatusSchema>;
export type ModelVersion = z.infer<typeof ModelVersionSchema>;
