/**
 * Data Thresholds for Intelligence Engines
 * 
 * These thresholds define the minimum data requirements for each intelligence
 * engine to transition from InsufficientDataState to operational state.
 * All values are derived from the recovered v2 bundle and the upgrade spec.
 */

export const DATA_THRESHOLDS = {
  /** Minimum days of logged history required for forecast generation */
  FORECAST_MIN_DAYS: 7,

  /** Minimum days of logged history required for trigger graph analysis */
  TRIGGER_GRAPH_MIN_DAYS: 14,

  /** Minimum number of face scans required for Skin Twin Lab */
  SKIN_TWIN_MIN_SCANS: 10,

  /** Minimum days of logged history required for barrier guard analysis */
  BARRIER_MIN_DAYS: 5,

  /** Minimum number of logs required for CHI (Cutis Health Index) */
  CHI_MIN_LOGS: 3,

  /** Minimum number of ingredients matched for product analysis confidence */
  PRODUCT_MIN_INGREDIENTS: 2,

  /** Minimum quality score for face scan validation (0-100) */
  MIN_IMAGE_QUALITY_SCORE: 0.6,

  /** Minimum confidence score for face analysis results (0-1) */
  MIN_FACE_CONFIDENCE: 0.7,
} as const;

/**
 * Validation status constants
 */
export const VALIDATION_STATUS = {
  PASSED: "passed",
  INSUFFICIENT_DATA: "insufficient_data",
  LOW_CONFIDENCE: "low_confidence",
  FAILED: "failed",
} as const;

/**
 * Model tier constants reflecting AI/ML readiness
 */
export const MODEL_TIER = {
  BOOTSTRAP: "bootstrap",
  DEVELOPING: "developing",
  CALIBRATED: "calibrated",
  ADVANCED: "advanced",
} as const;
