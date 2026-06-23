/**
 * useDoubleSubmitGuard Hook
 * 
 * Provides race condition protection for form submissions and AI-triggering actions.
 * Uses a mutable ref-based guard in addition to React's useState to prevent
 * double-submission issues in concurrent mode.
 * 
 * In concurrent mode, batched state updates may not disable the button before
 * a second click event fires, so this hook uses both a ref and state for safety.
 */

import { useRef, useState, useCallback } from "react";

export interface UseDoubleSubmitGuardReturn {
  /** Whether a submission is currently in progress */
  isSubmitting: boolean;

  /** Function to call when starting a submission */
  startSubmission: () => boolean;

  /** Function to call when a submission completes */
  endSubmission: () => void;

  /** Function to call when a submission fails */
  failSubmission: () => void;

  /** Wrapper function for async submission handlers */
  withGuard: <T extends unknown[], R>(
    handler: (...args: T) => Promise<R>
  ) => (...args: T) => Promise<R | undefined>;
}

/**
 * Hook that provides double-submit protection for form submissions and
 * AI-triggering actions.
 * 
 * @returns Object with submission state and guard functions
 */
export function useDoubleSubmitGuard(): UseDoubleSubmitGuardReturn {
  const submittingRef = useRef(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const startSubmission = useCallback((): boolean => {
    if (submittingRef.current) {
      return false;
    }
    submittingRef.current = true;
    setIsSubmitting(true);
    return true;
  }, []);

  const endSubmission = useCallback(() => {
    submittingRef.current = false;
    setIsSubmitting(false);
  }, []);

  const failSubmission = useCallback(() => {
    submittingRef.current = false;
    setIsSubmitting(false);
  }, []);

  const withGuard = useCallback(
    <T extends unknown[], R>(
      handler: (...args: T) => Promise<R>
    ): ((...args: T) => Promise<R | undefined>) => {
      return async (...args: T): Promise<R | undefined> => {
        if (!startSubmission()) {
          return undefined;
        }

        try {
          const result = await handler(...args);
          endSubmission();
          return result;
        } catch (error) {
          failSubmission();
          throw error;
        }
      };
    },
    [startSubmission, endSubmission, failSubmission]
  );

  return {
    isSubmitting,
    startSubmission,
    endSubmission,
    failSubmission,
    withGuard,
  };
}

export default useDoubleSubmitGuard;
