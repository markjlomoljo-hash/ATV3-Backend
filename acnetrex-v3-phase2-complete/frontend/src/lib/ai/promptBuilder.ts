/**
 * Prompt Builder Utility
 * 
 * Manages token budgets and context windows for InvokeLLM prompts.
 * Assembles context sections in priority order, measures character length,
 * and truncates lower-priority sections before higher-priority ones.
 * 
 * Maximum prompt sizes:
 * - CutisAI assistant: 12,000 characters
 * - Forecasting engine: 8,000 characters
 * - FaceAtlas text portion: 2,000 characters
 * - Product/ingredient analysis: 6,000 characters
 * - Research retrieval synthesis: 8,000 characters
 */

export interface PromptSection {
  /** Unique identifier for the section */
  id: string;

  /** Priority level (higher = more important, never truncate) */
  priority: number;

  /** Content of the section */
  content: string;

  /** Optional label for logging/debugging */
  label?: string;
}

export interface PromptBuilderResult {
  /** Final assembled prompt */
  prompt: string;

  /** Character count of the final prompt */
  characterCount: number;

  /** Whether any truncation occurred */
  wasTruncated: boolean;

  /** List of sections that were truncated */
  truncatedSections: string[];

  /** Warning message if truncation occurred */
  warning?: string;
}

/**
 * Builds a safe prompt by assembling sections in priority order and
 * truncating lower-priority sections if necessary to stay within the
 * character limit.
 * 
 * @param sections - Array of prompt sections
 * @param maxChars - Maximum character limit for the prompt
 * @returns PromptBuilderResult with the assembled prompt and metadata
 */
export function buildSafePrompt(
  sections: PromptSection[],
  maxChars: number
): PromptBuilderResult {
  // Sort sections by priority (descending)
  const sorted = [...sections].sort((a, b) => b.priority - a.priority);

  let prompt = "";
  let wasTruncated = false;
  const truncatedSections: string[] = [];

  for (const section of sorted) {
    const testPrompt = prompt + (prompt ? "\n\n" : "") + section.content;

    if (testPrompt.length <= maxChars) {
      prompt = testPrompt;
    } else {
      // This section would exceed the limit
      wasTruncated = true;
      truncatedSections.push(section.label || section.id);

      // Try to fit a truncated version of this section if it's not the highest priority
      if (section.priority < sorted[0].priority) {
        const availableSpace = maxChars - prompt.length - 4; // -4 for separators
        if (availableSpace > 100) {
          const truncated = section.content.substring(0, availableSpace - 3) + "...";
          const testTruncated = prompt + (prompt ? "\n\n" : "") + truncated;
          if (testTruncated.length <= maxChars) {
            prompt = testTruncated;
          }
        }
      }
    }
  }

  const warning = wasTruncated
    ? `Prompt truncated: ${truncatedSections.join(", ")} sections were reduced or excluded to stay within ${maxChars} character limit.`
    : undefined;

  return {
    prompt,
    characterCount: prompt.length,
    wasTruncated,
    truncatedSections,
    warning,
  };
}

/**
 * Creates a prompt for CutisAI assistant with proper context management
 */
export function buildCutisAIPrompt(
  userQuestion: string,
  onboardingProfile: string,
  recentLogs: string,
  latestScan: string,
  recentForecast: string,
  conversationHistory: string
): PromptBuilderResult {
  const sections: PromptSection[] = [
    {
      id: "user_question",
      priority: 100,
      content: `User Question: ${userQuestion}`,
      label: "User Question",
    },
    {
      id: "onboarding",
      priority: 90,
      content: `Onboarding Profile:\n${onboardingProfile}`,
      label: "Onboarding Profile",
    },
    {
      id: "conversation",
      priority: 80,
      content: `Recent Conversation:\n${conversationHistory}`,
      label: "Conversation History",
    },
    {
      id: "logs",
      priority: 60,
      content: `Recent Logs (Last 7 Days):\n${recentLogs}`,
      label: "Recent Logs",
    },
    {
      id: "scan",
      priority: 50,
      content: `Latest Face Scan:\n${latestScan}`,
      label: "Latest Scan",
    },
    {
      id: "forecast",
      priority: 40,
      content: `Recent Forecast:\n${recentForecast}`,
      label: "Recent Forecast",
    },
  ];

  return buildSafePrompt(sections, 12000);
}

/**
 * Creates a prompt for forecasting engine with proper context management
 */
export function buildForecastingPrompt(
  currentCondition: string,
  triggerCorrelations: string,
  historicalLogs: string,
  userGoals: string
): PromptBuilderResult {
  const sections: PromptSection[] = [
    {
      id: "current",
      priority: 100,
      content: `Current Skin Condition:\n${currentCondition}`,
      label: "Current Condition",
    },
    {
      id: "triggers",
      priority: 90,
      content: `Trigger Correlations:\n${triggerCorrelations}`,
      label: "Trigger Correlations",
    },
    {
      id: "history",
      priority: 70,
      content: `Historical Data Summary:\n${historicalLogs}`,
      label: "Historical Logs",
    },
    {
      id: "goals",
      priority: 60,
      content: `User Goals:\n${userGoals}`,
      label: "User Goals",
    },
  ];

  return buildSafePrompt(sections, 8000);
}

/**
 * Creates a prompt for product analysis with proper context management
 */
export function buildProductAnalysisPrompt(
  productInfo: string,
  ingredientList: string,
  userProfile: string,
  relevantStudies: string
): PromptBuilderResult {
  const sections: PromptSection[] = [
    {
      id: "product",
      priority: 100,
      content: `Product Information:\n${productInfo}`,
      label: "Product Info",
    },
    {
      id: "ingredients",
      priority: 95,
      content: `Ingredient List:\n${ingredientList}`,
      label: "Ingredients",
    },
    {
      id: "profile",
      priority: 80,
      content: `User Skin Profile:\n${userProfile}`,
      label: "User Profile",
    },
    {
      id: "studies",
      priority: 60,
      content: `Relevant Research:\n${relevantStudies}`,
      label: "Research",
    },
  ];

  return buildSafePrompt(sections, 6000);
}
