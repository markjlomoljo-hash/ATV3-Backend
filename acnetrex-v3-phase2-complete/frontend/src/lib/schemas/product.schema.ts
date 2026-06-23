/**
 * Product Zod Schema
 * 
 * Runtime validation for product scan records from the backend.
 * Ensures all product data crossing the service boundary conforms to
 * the expected shape before rendering in components.
 */

import { z } from "zod";

/**
 * Risk contribution for a single ingredient
 */
export const RiskContributionSchema = z.object({
  comedogenic_rating: z.number().min(0).max(5).nullable(),
  irritant_risk: z.number().min(0).max(100).nullable(),
  barrier_support: z.number().min(-100).max(100).nullable(),
  acne_association: z.string().nullable(),
}).strict();

/**
 * Ingredient result from product analysis
 */
export const ProductIngredientResultSchema = z.object({
  id: z.string().uuid(),
  product_scan_id: z.string().uuid(),
  ingredient_profile_id: z.string().uuid().nullable(),
  matched_text: z.string(),
  position_in_list: z.number().int().nonnegative(),
  risk_contribution: RiskContributionSchema,
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
}).strict();

/**
 * Complete ProductScan record from backend
 */
export const ProductScanSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  product_name: z.string(),
  brand: z.string().nullable(),
  category: z.string().nullable(),
  input_method: z.enum(["manual", "ocr", "barcode"]),
  image_s3_key: z.string().nullable(),
  raw_ingredient_text: z.string(),
  overall_risk: z.number().min(0).max(100),
  comedogenic_score: z.number().min(0).max(100),
  irritation_risk: z.number().min(0).max(100),
  barrier_support_score: z.number().min(-100).max(100),
  acne_trigger_likelihood: z.enum(["low", "moderate", "high"]),
  conclusion: z.string(),
  confidence_level: z.number().min(0).max(1),
  model_version: z.string(),
  in_routine: z.boolean(),
  added_at: z.string().datetime(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  app_version: z.string(),
  schema_version: z.string(),
  source: z.string(),
  ingredients: z.array(ProductIngredientResultSchema).optional(),
}).strict();

export type ProductScan = z.infer<typeof ProductScanSchema>;
export type ProductIngredientResult = z.infer<typeof ProductIngredientResultSchema>;
export type RiskContribution = z.infer<typeof RiskContributionSchema>;
