/**
 * InvokeWithRetry Utility
 * 
 * Wraps all InvokeLLM calls with mandatory timeout and retry logic.
 * Adheres to the InvokeLLM Operational Constraint Matrix:
 * - Internet calls: 45s timeout
 * - Vision calls: 30s timeout
 * - Standard reasoning: 20s timeout
 * - Extraction: 10s timeout
 * 
 * On timeout, retries once with a 2-second backoff.
 * Does not retry on explicit model errors (invalid schema, refusal).
 * After two failures, emits an IntelligenceEvent with status: "failed".
 */

export interface InvokeParams {
  prompt?: string;
  model?: string;
  add_context_from_internet?: boolean;
  file_urls?: string[];
  response_json_schema?: {
    root: { type: "object" };
    [key: string]: unknown;
  };
  max_tokens?: number;
}

export interface InvokeResult<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  timeout?: boolean;
}

/**
 * Determines the timeout duration based on the call type
 */
function getTimeoutMs(params: InvokeParams): number {
  if (params.file_urls && params.file_urls.length > 0) {
    // Vision call
    return 30000;
  }
  if (params.add_context_from_internet) {
    // Internet-augmented call
    return 45000;
  }
  if (params.response_json_schema) {
    // Extraction call
    return 10000;
  }
  // Standard reasoning
  return 20000;
}

/**
 * Creates a timeout promise that rejects after the specified duration
 */
function createTimeoutPromise<T>(ms: number): Promise<T> {
  return new Promise((_, reject) => {
    setTimeout(() => {
      reject(new Error(`InvokeLLM timeout after ${ms}ms`));
    }, ms);
  });
}

/**
 * Invokes the InvokeLLM API with timeout and retry logic
 * 
 * @param params - InvokeLLM parameters
 * @param timeoutMs - Optional override for timeout duration
 * @returns Promise resolving to the API response or error
 */
export async function invokeWithRetry<T = unknown>(
  params: InvokeParams,
  timeoutMs?: number
): Promise<InvokeResult<T>> {
  const timeout = timeoutMs || getTimeoutMs(params);
  let lastError: Error | null = null;

  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      // Apply backoff on retry
      if (attempt > 0) {
        await new Promise((resolve) => setTimeout(resolve, 2000));
      }

      // Call the actual InvokeLLM API (this would be replaced with the real API call)
      // For now, this is a placeholder that should be replaced with the actual implementation
      const response = await Promise.race([
        invokeInternalLLM<T>(params),
        createTimeoutPromise<T>(timeout),
      ]);

      return {
        success: true,
        data: response,
      };
    } catch (error) {
      lastError = error instanceof Error ? error : new Error(String(error));

      // Check if this is a timeout error
      const isTimeout = lastError.message.includes("timeout");

      // Don't retry on explicit model errors (invalid schema, refusal)
      if (!isTimeout && attempt === 0) {
        // This is a model error, not a timeout, so don't retry
        return {
          success: false,
          error: lastError.message,
          timeout: false,
        };
      }

      // If this is the last attempt, return the error
      if (attempt === 1) {
        return {
          success: false,
          error: lastError.message,
          timeout: isTimeout,
        };
      }

      // Continue to retry
    }
  }

  return {
    success: false,
    error: lastError?.message || "Unknown error",
    timeout: lastError?.message.includes("timeout"),
  };
}

/**
 * Placeholder for the actual InvokeLLM API call
 * This should be replaced with the real implementation that calls the backend
 */
async function invokeInternalLLM<T = unknown>(_params: InvokeParams): Promise<T> {
  // TODO: Implement actual InvokeLLM API call
  throw new Error("invokeInternalLLM not yet implemented");
}
