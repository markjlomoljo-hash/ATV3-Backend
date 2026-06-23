/**
 * EmptyState Component
 * 
 * Shared component for rendering empty states when no data exists for a module.
 * Adheres to the Zero-Fabrication Contract: no invented values are substituted
 * for missing real data. Instead, a clear, actionable empty state is rendered.
 */

import React from "react";
import { LucideIcon } from "lucide-react";

export interface EmptyStateProps {
  /** Icon to display (from lucide-react) */
  icon: LucideIcon;

  /** Title of the empty state */
  title: string;

  /** Description explaining why the state is empty */
  description: string;

  /** Label for the call-to-action button */
  ctaLabel: string;

  /** Route to navigate to when CTA is clicked */
  ctaRoute: string;

  /** Optional callback when CTA is clicked (overrides navigation if provided) */
  onCtaClick?: () => void;
}

/**
 * EmptyState renders a polished, mobile-friendly empty state with an icon,
 * descriptive text, and a call-to-action button.
 */
export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon,
  title,
  description,
  ctaLabel,
  ctaRoute,
  onCtaClick,
}) => {
  const handleClick = () => {
    if (onCtaClick) {
      onCtaClick();
    } else {
      window.location.href = ctaRoute;
    }
  };

  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="mb-6 text-gray-300">
        <Icon size={64} strokeWidth={1.5} />
      </div>
      <h2 className="mb-2 text-2xl font-semibold text-gray-900">{title}</h2>
      <p className="mb-8 max-w-md text-center text-gray-600">{description}</p>
      <button
        onClick={handleClick}
        className="rounded-lg bg-blue-600 px-6 py-2.5 font-medium text-white transition-colors hover:bg-blue-700 active:bg-blue-800"
      >
        {ctaLabel}
      </button>
    </div>
  );
};

export default EmptyState;
