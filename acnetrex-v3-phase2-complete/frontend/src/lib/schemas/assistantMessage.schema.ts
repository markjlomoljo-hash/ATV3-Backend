/**
 * AssistantMessage Zod Schema
 * 
 * Runtime validation for assistant conversation records from the backend.
 * Ensures all message data crossing the service boundary conforms to
 * the expected shape before rendering in components.
 */

import { z } from "zod";

/**
 * Context used for assistant message generation
 */
export const ContextUsedSchema = z.object({
  has_health_index: z.boolean(),
  has_scan: z.boolean(),
  sleep_log_count: z.number().int().nonnegative(),
  food_log_count: z.number().int().nonnegative(),
  stress_log_count: z.number().int().nonnegative(),
  product_count: z.number().int().nonnegative(),
  evidence_retrieved: z.number().int().nonnegative(),
  evidence_retrieval_method: z.enum(["keyword", "semantic", "none"]),
}).strict();

/**
 * Single message in a conversation
 */
export const AssistantMessageSchema = z.object({
  id: z.string().uuid(),
  conversation_id: z.string().uuid(),
  role: z.enum(["user", "assistant"]),
  content: z.string(),
  confidence: z.number().min(0).max(1).nullable(),
  evidence_source_ids: z.array(z.string().uuid()).default([]),
  context_used: ContextUsedSchema.nullable(),
  self_check_passed: z.boolean().nullable(),
  self_check_notes: z.string().nullable(),
  model_version: z.string().nullable(),
  escalation_flag: z.boolean(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  app_version: z.string(),
  schema_version: z.string(),
  source: z.string(),
}).strict();

/**
 * Conversation record
 */
export const AssistantConversationSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string().uuid(),
  title: z.string().nullable(),
  last_message_at: z.string().datetime().nullable(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  app_version: z.string(),
  schema_version: z.string(),
  source: z.string(),
  messages: z.array(AssistantMessageSchema).optional(),
}).strict();

export type AssistantMessage = z.infer<typeof AssistantMessageSchema>;
export type AssistantConversation = z.infer<typeof AssistantConversationSchema>;
export type ContextUsed = z.infer<typeof ContextUsedSchema>;
