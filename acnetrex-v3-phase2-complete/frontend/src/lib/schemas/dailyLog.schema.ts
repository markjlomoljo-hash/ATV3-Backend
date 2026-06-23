/**
 * DailyLog Zod Schema
 * 
 * Runtime validation for daily log records from the backend.
 * Ensures all log data crossing the service boundary conforms to
 * the expected shape before rendering in components.
 */

import { z } from "zod";

/**
 * Sleep log data
 */
export const SleepLogDataSchema = z.object({
  bedtime: z.string(),
  wakeTime: z.string(),
  netSleepHours: z.number().min(0).max(24),
  quality: z.enum(["poor", "fair", "good", "excellent"]),
  fragmented: z.boolean(),
  lateNightShift: z.boolean(),
  sleepDebt: z.number().min(0).max(24),
}).strict();

/**
 * Food log data
 */
export const FoodLogDataSchema = z.object({
  meals: z.array(z.object({
    id: z.string().uuid(),
    name: z.string(),
    category: z.string(),
    riskScore: z.number().min(0).max(100),
  })),
  hydrationLiters: z.number().min(0),
  glycemicLoad: z.number().min(0).max(100),
  dairyIntake: z.boolean(),
  wheyProtein: z.boolean(),
  sugarLoad: z.enum(["low", "moderate", "high"]),
  processedFoodLevel: z.enum(["low", "moderate", "high"]),
  overallRisk: z.number().min(0).max(100),
}).strict();

/**
 * Activity log data
 */
export const ActivityLogDataSchema = z.object({
  activityType: z.string(),
  intensity: z.enum(["light", "moderate", "vigorous"]),
  durationMinutes: z.number().int().positive(),
  sweatLevel: z.enum(["none", "light", "moderate", "heavy"]),
  postWorkoutCleansDelay: z.number().int().nonnegative(),
  frictionFactors: z.array(z.string()).default([]),
  breakoutRisk: z.number().min(0).max(100),
}).strict();

/**
 * Stress log data
 */
export const StressLogDataSchema = z.object({
  stressLevel: z.number().min(1).max(10),
  stressType: z.array(z.string()).default([]),
  copingStrategy: z.string().nullable(),
}).strict();

/**
 * Contact log data
 */
export const ContactLogDataSchema = z.object({
  contactType: z.enum(["face_touching", "phone_contact", "pillow_contact", "other"]),
  frequency: z.enum(["rarely", "occasionally", "frequently"]),
  cleanlinessLevel: z.enum(["poor", "fair", "good", "excellent"]),
}).strict();

/**
 * Hydration log data
 */
export const HydrationLogDataSchema = z.object({
  waterIntakeLiters: z.number().min(0),
  targetLiters: z.number().min(0),
  metTarget: z.boolean(),
}).strict();

/**
 * Cycle log data
 */
export const CycleLogDataSchema = z.object({
  cyclePhase: z.enum(["menstrual", "follicular", "ovulation", "luteal"]),
  flowIntensity: z.enum(["light", "moderate", "heavy"]).nullable(),
  symptoms: z.array(z.string()).default([]),
}).strict();

/**
 * Union type for all log data
 */
export const LogDataSchema = z.union([
  SleepLogDataSchema,
  FoodLogDataSchema,
  ActivityLogDataSchema,
  StressLogDataSchema,
  ContactLogDataSchema,
  HydrationLogDataSchema,
  CycleLogDataSchema,
]);

/**
 * Complete DailyLog record from backend
 */
export const DailyLogSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  log_date: z.string().date(),
  log_type: z.enum(["sleep", "food", "stress", "activity", "contact", "hydration", "cycle"]),
  data: LogDataSchema,
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  app_version: z.string(),
  schema_version: z.string(),
  source: z.string(),
}).strict();

export type DailyLog = z.infer<typeof DailyLogSchema>;
export type SleepLogData = z.infer<typeof SleepLogDataSchema>;
export type FoodLogData = z.infer<typeof FoodLogDataSchema>;
export type ActivityLogData = z.infer<typeof ActivityLogDataSchema>;
export type StressLogData = z.infer<typeof StressLogDataSchema>;
export type ContactLogData = z.infer<typeof ContactLogDataSchema>;
export type HydrationLogData = z.infer<typeof HydrationLogDataSchema>;
export type CycleLogData = z.infer<typeof CycleLogDataSchema>;
