/**
 * InsufficientDataState Component
 * 
 * Shared component for rendering states when data exists but is below the
 * minimum threshold for meaningful analysis. Displays progress toward the
 * required data points and encourages continued data collection.
 */

import React from "react";

export interface InsufficientDataStateProps {
  /** Name of the module (e.g., "Forecast", "Skin Twin Lab") */
  moduleName: string;

  /** Required number of data points for the module to operate */
  requiredDataPoints: number;

  /** Current number of data points collected */
  currentDataPoints: number;

  /** Label for the call-to-action button */
  ctaLabel: string;

  /** Route to navigate to when CTA is clicked */
  ctaRoute: string;

  /** Optional callback when CTA is clicked (overrides navigation if provided) */
  onCtaClick?: () => void;
}

/**
 * InsufficientDataState renders a progress bar showing how close the user is
 * to meeting the minimum data requirements for a module to become operational.
 */
export const InsufficientDataState: React.FC<InsufficientDataStateProps> = ({
  moduleName,
  requiredDataPoints,
  currentDataPoints,
  ctaLabel,
  ctaRoute,
  onCtaClick,
}) => {
  const progress = Math.min((currentDataPoints / requiredDataPoints) * 100, 100);
  const remaining = Math.max(requiredDataPoints - currentDataPoints, 0);

  const handleClick = () => {
    if (onCtaClick) {
      onCtaClick();
    } else {
      window.location.href = ctaRoute;
    }
  };

  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <h2 className="mb-4 text-2xl font-semibold text-gray-900">
        {moduleName} Coming Soon
      </h2>
      <p className="mb-6 max-w-md text-center text-gray-600">
        We're collecting data to power {moduleName}. Keep logging to unlock
        advanced insights.
      </p>

      <div className="w-full max-w-md">
        <div className="mb-3 flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">
            Progress
          </span>
          <span className="text-sm font-medium text-gray-700">
            {currentDataPoints} / {requiredDataPoints}
          </span>
        </div>

        <div className="h-2 w-full overflow-hidden rounded-full bg-gray-200">
          <div
            className="h-full bg-blue-600 transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>

        <p className="mt-3 text-center text-sm text-gray-600">
          {remaining > 0
            ? `${remaining} more ${remaining === 1 ? "entry" : "entries"} needed`
            : "Ready to analyze!"}
        </p>
      </div>

      <button
        onClick={handleClick}
        className="mt-8 rounded-lg bg-blue-600 px-6 py-2.5 font-medium text-white transition-colors hover:bg-blue-700 active:bg-blue-800"
      >
        {ctaLabel}
      </button>
    </div>
  );
};

export default InsufficientDataState;
