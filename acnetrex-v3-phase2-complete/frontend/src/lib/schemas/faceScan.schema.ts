/**
 * FaceScan Zod Schema
 * 
 * Runtime validation for face scan records from the backend.
 * Ensures all FaceScan data crossing the service boundary conforms to
 * the expected shape before rendering in components.
 */

import { z } from "zod";

/**
 * Zone analysis data for a face scan
 */
export const ZoneSchema = z.object({
  zone_name: z.string(),
  lesion_count: z.number().int().nonnegative(),
  redness_score: z.number().min(0).max(100),
  oiliness_score: z.number().min(0).max(100),
  dryness_score: z.number().min(0).max(100),
  pih_score: z.number().min(0).max(100),
  pie_score: z.number().min(0).max(100),
  scar_visibility: z.number().min(0).max(100),
}).strict();

/**
 * Lesion classification data
 */
export const LesionSchema = z.object({
  lesion_id: z.string().uuid(),
  type: z.enum(["comedone", "papule", "pustule", "nodule", "cyst", "pih", "pie", "scar"]),
  zone: z.string(),
  severity: z.enum(["mild", "moderate", "severe"]),
  confidence: z.number().min(0).max(1),
}).strict();

/**
 * Complete FaceScan record from backend
 */
export const FaceScanSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  scan_type: z.enum(["baseline", "daily"]),
  captured_at: z.string().datetime(),
  image_s3_key: z.string().nullable(),
  image_consent: z.boolean(),
  zones: z.record(ZoneSchema).default({}),
  lesions: z.record(LesionSchema).default({}),
  lesion_count: z.number().int().nonnegative(),
  quality_score: z.number().min(0).max(1),
  is_valid_face: z.boolean(),
  confidence_score: z.number().min(0).max(1),
  redness_score: z.number().min(0).max(100).nullable(),
  oiliness_score: z.number().min(0).max(100).nullable(),
  dryness_score: z.number().min(0).max(100).nullable(),
  validation_status: z.enum(["passed", "insufficient_data", "low_confidence", "failed", "pending_analysis"]),
  model_version: z.string(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  app_version: z.string(),
  schema_version: z.string(),
  source: z.string(),
}).strict();

export type FaceScan = z.infer<typeof FaceScanSchema>;
export type Zone = z.infer<typeof ZoneSchema>;
export type Lesion = z.infer<typeof LesionSchema>;
