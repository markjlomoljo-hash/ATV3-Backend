/**
 * AcneTrex v3 typed API client.
 *
 * Every frontend component that needs backend data should import from here,
 * not build its own fetch calls. This is the single place where:
 * - The base URL is read from VITE_API_BASE_URL
 * - The bearer token is attached from localStorage (v3 token only)
 * - Error shapes are normalized to ApiError so callers don't parse raw HTTP
 * - Token refresh / 401 -> sign-out redirect is handled in one place
 *
 * localStorage usage here is intentionally narrow:
 *   acnetrex_token_v3   - current JWT (written on login, cleared on logout)
 *   acnetrex_expires_v3 - expiry ISO string (for proactive refresh)
 * The old acnetrex_credentials / acnetrex_auth_v2 / acnetrex_data_v2 /
 * acnetrex_ai_v2 keys are read ONCE by the migration flow (migrationApi)
 * and then cleared. They must never be read again by any other part of
 * the app after migration.
 */

const BASE_URL = (import.meta.env.VITE_API_BASE_URL as string) || "http://localhost:8000/v1";
const TOKEN_KEY = "acnetrex_token_v3";
const EXPIRES_KEY = "acnetrex_expires_v3";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string,
    message: string,
    public readonly details?: Record<string, unknown>
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

function setToken(token: string, expiresAt: string): void {
  localStorage.setItem(TOKEN_KEY, token);
  localStorage.setItem(EXPIRES_KEY, expiresAt);
}

function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(EXPIRES_KEY);
}

async function request<T>(
  endpoint: string,
  options: RequestInit = {},
  isFormData = false
): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (!isFormData) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const res = await fetch(`${BASE_URL}${endpoint}`, { ...options, headers });

  if (res.status === 401) {
    clearToken();
    // Let the Zustand auth store / router handle the redirect
    window.dispatchEvent(new Event("acnetrex:session-expired"));
    const err = await res.json().catch(() => ({}));
    throw new ApiError(401, err.error ?? "session_expired", err.message ?? "Your session has expired. Please sign in again.");
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new ApiError(
      res.status,
      err.error ?? "request_failed",
      err.message ?? `Request failed with status ${res.status}`,
      err.details
    );
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

// ─── Auth ─────────────────────────────────────────────────────────────────────

export interface UserOut {
  id: string;
  email: string;
  display_name: string;
  email_verified: boolean;
  created_at: string;
  last_login_at: string | null;
}

export interface AuthResponse {
  user: UserOut;
  access_token: string;
  expires_at: string;
  onboarding_completed: boolean;
}

export const authApi = {
  async signup(email: string, password: string, displayName: string): Promise<AuthResponse> {
    const data = await request<AuthResponse>("/auth/signup", {
      method: "POST",
      body: JSON.stringify({ email, password, display_name: displayName }),
    });
    setToken(data.access_token, data.expires_at);
    return data;
  },

  async login(email: string, password: string, rememberMe = false): Promise<AuthResponse> {
    const data = await request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password, remember_me: rememberMe }),
    });
    setToken(data.access_token, data.expires_at);
    return data;
  },

  async logout(): Promise<void> {
    await request<void>("/auth/logout", { method: "POST" });
    clearToken();
  },

  async me(): Promise<UserOut> {
    return request<UserOut>("/auth/me");
  },

  async forgotPassword(email: string): Promise<void> {
    return request<void>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    });
  },

  async resetPassword(token: string, newPassword: string): Promise<void> {
    return request<void>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password: newPassword }),
    });
  },

  /** One-time legacy data import. Reads legacy localStorage keys, sends to
   * the backend migration endpoint, then clears the legacy keys. */
  async migrateLegacyData(): Promise<{ imported: number; skipped: number; failed: number }> {
    const legacyAuthV2 = (() => {
      try { return JSON.parse(localStorage.getItem("acnetrex_auth_v2") ?? "null"); } catch { return null; }
    })();
    const legacyDataV2 = (() => {
      try { return JSON.parse(localStorage.getItem("acnetrex_data_v2") ?? "null"); } catch { return null; }
    })();
    const legacyAiV2 = (() => {
      try { return JSON.parse(localStorage.getItem("acnetrex_ai_v2") ?? "null"); } catch { return null; }
    })();

    if (!legacyAuthV2 && !legacyDataV2 && !legacyAiV2) {
      return { imported: 0, skipped: 0, failed: 0 };
    }

    const result = await request<{ imported: number; skipped: number; failed: number }>("/auth/migrate", {
      method: "POST",
      body: JSON.stringify({
        consent_to_import: true,
        legacy_auth_v2: legacyAuthV2,
        legacy_data_v2: legacyDataV2,
        legacy_ai_v2: legacyAiV2,
      }),
    });

    // Clear legacy keys after successful import
    localStorage.removeItem("acnetrex_credentials");
    localStorage.removeItem("acnetrex_auth_v2");
    localStorage.removeItem("acnetrex_data_v2");
    localStorage.removeItem("acnetrex_ai_v2");
    return result;
  },

  isAuthenticated(): boolean {
    const token = getToken();
    const expires = localStorage.getItem(EXPIRES_KEY);
    if (!token || !expires) return false;
    return new Date(expires) > new Date();
  },
};

// ─── Profile ──────────────────────────────────────────────────────────────────

export const profileApi = {
  async get(): Promise<UserOut> {
    return request<UserOut>("/profile");
  },
  async patch(displayName: string): Promise<UserOut> {
    return request<UserOut>("/profile", {
      method: "PATCH",
      body: JSON.stringify({ display_name: displayName }),
    });
  },
};

// ─── Onboarding ───────────────────────────────────────────────────────────────

export interface OnboardingOut {
  user_id: string;
  age: number | null;
  sex: string | null;
  height_cm: number | null;
  weight_kg: number | null;
  skin_type: string | null;
  acne_type: string | null;
  acne_severity: string | null;
  skin_goals: string[];
  sleep_hours: number | null;
  stress_level: number | null;
  diet_type: string | null;
  health_conditions: string[];
  maintenance_medications: string[];
  track_cycle: boolean;
  baseline_scan_completed: boolean;
  completed: boolean;
  current_step: number;
  completed_at: string | null;
}

export const onboardingApi = {
  async get(): Promise<OnboardingOut> {
    return request<OnboardingOut>("/onboarding");
  },
  async patch(updates: Partial<OnboardingOut>): Promise<OnboardingOut> {
    return request<OnboardingOut>("/onboarding", {
      method: "PATCH",
      body: JSON.stringify(updates),
    });
  },
  async complete(): Promise<OnboardingOut> {
    return request<OnboardingOut>("/onboarding/complete", { method: "POST" });
  },
};

// ─── Logs ─────────────────────────────────────────────────────────────────────

export interface DailyLogOut {
  id: string;
  user_id: string;
  log_date: string;
  log_type: string;
  data: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  was_merged: boolean;
}

export const logsApi = {
  async getToday(forDate?: string): Promise<DailyLogOut[]> {
    const qs = forDate ? `?for_date=${forDate}` : "";
    return request<DailyLogOut[]>(`/logs/today${qs}`);
  },
  async logSleep(payload: {
    log_date?: string; bedtime: string; wake_time: string; quality: number; fragmented?: boolean; late_night_shift?: boolean;
  }): Promise<DailyLogOut> {
    return request<DailyLogOut>("/logs/sleep", { method: "POST", body: JSON.stringify(payload) });
  },
  async logFood(payload: {
    log_date?: string; meals: { name: string }[]; hydration_liters: number; glycemic_load: number;
    dairy_intake?: boolean; whey_protein?: boolean; sugar_load?: string; processed_food_level?: string;
  }): Promise<DailyLogOut> {
    return request<DailyLogOut>("/logs/food", { method: "POST", body: JSON.stringify(payload) });
  },
  async logStress(payload: {
    log_date?: string; stress_level: number; mood: string; anxiety_level: number; workload: string; major_event?: string;
  }): Promise<DailyLogOut> {
    return request<DailyLogOut>("/logs/stress", { method: "POST", body: JSON.stringify(payload) });
  },
  async logActivity(payload: {
    log_date?: string; activity_type: string; intensity: string; duration_minutes: number;
    sweat_level: string; post_workout_cleanse_delay_minutes: number; friction_factors?: string[];
  }): Promise<DailyLogOut> {
    return request<DailyLogOut>("/logs/activity", { method: "POST", body: JSON.stringify(payload) });
  },
  async logContact(payload: {
    log_date?: string; pillowcase_changed?: boolean; phone_screen_cleaned?: boolean; mask_worn?: boolean;
    helmet_worn?: boolean; touched_face?: boolean; hair_product_contact?: boolean; makeup_worn?: boolean; makeup_removed?: boolean;
  }): Promise<DailyLogOut> {
    return request<DailyLogOut>("/logs/contact", { method: "POST", body: JSON.stringify(payload) });
  },
  async logHydration(payload: {
    log_date?: string; water_intake_liters: number; target_liters?: number;
  }): Promise<DailyLogOut> {
    return request<DailyLogOut>("/logs/hydration", { method: "POST", body: JSON.stringify(payload) });
  },
  async logCycle(payload: {
    log_date?: string; cycle_day?: number; phase?: string; symptoms?: string[]; flow_level?: string;
  }): Promise<DailyLogOut> {
    return request<DailyLogOut>("/logs/cycle", { method: "POST", body: JSON.stringify(payload) });
  },
};

// ─── Scans ────────────────────────────────────────────────────────────────────

export interface ScanOut {
  id: string;
  scan_type: string;
  captured_at: string;
  overall_condition: string | null;
  lesion_count: number;
  redness_score: number | null;
  confidence_score: number;
  validation_status: string;
  model_version: string;
  image_stored: boolean;
  image_consent: boolean;
  zones: Record<string, unknown>;
  lesions: Record<string, unknown>;
  source: string;
}

export const scansApi = {
  async create(scanType: string, imageFile: File | null, imageConsent: boolean): Promise<ScanOut> {
    const formData = new FormData();
    formData.append("scan_type", scanType);
    formData.append("image_consent", String(imageConsent));
    if (imageFile) formData.append("image", imageFile);
    return request<ScanOut>("/scans", { method: "POST", body: formData }, true);
  },
  async list(): Promise<ScanOut[]> {
    return request<ScanOut[]>("/scans");
  },
  async get(scanId: string): Promise<ScanOut> {
    return request<ScanOut>(`/scans/${scanId}`);
  },
  async analyze(scanId: string): Promise<ScanOut> {
    return request<ScanOut>(`/scans/${scanId}/analyze`, { method: "POST" });
  },
};

// ─── Products ─────────────────────────────────────────────────────────────────

export interface ProductScanOut {
  id: string;
  product_name: string;
  brand: string | null;
  overall_risk: number | null;
  comedogenic_score: number | null;
  irritation_risk: number | null;
  barrier_support_score: number | null;
  acne_trigger_likelihood: number | null;
  conclusion: string | null;
  confidence_level: number | null;
  in_routine: boolean;
  added_at: string;
  source: string;
}

export const productsApi = {
  async analyze(payload: {
    product_name: string; brand?: string; category?: string; input_method?: string; raw_ingredient_text: string;
  }): Promise<ProductScanOut> {
    return request<ProductScanOut>("/products/analyze", { method: "POST", body: JSON.stringify(payload) });
  },
  async list(): Promise<ProductScanOut[]> {
    return request<ProductScanOut[]>("/products");
  },
  async toggleRoutine(productId: string, inRoutine: boolean): Promise<ProductScanOut> {
    return request<ProductScanOut>(`/products/${productId}`, {
      method: "PATCH", body: JSON.stringify({ in_routine: inRoutine }),
    });
  },
};

// ─── Forecast & Health Index ──────────────────────────────────────────────────

export interface HealthIndexOut {
  id: string;
  computed_at: string;
  overall_score: number;
  status: string;
  components: {
    barrierIntegrity: number;
    inflammationLoad: number;
    breakoutPressure: number;
    oilDryBalance: number;
    healingVelocity: number;
    sensitivityRisk: number;
  };
  driving_factors: string[];
  data_density: string;
  validation_status: string;
}

export interface ForecastOut {
  id: string;
  generated_at: string;
  horizon: string;
  current_risk: number;
  forecasted_risk: number;
  best_case_risk: number;
  worst_case_risk: number;
  confidence: number;
  validation_status: string;
  key_drivers: Array<{ factor: string }>;
  recommendations: string[];
  estimated_improvement_days: number;
}

export const forecastApi = {
  async getLatestHealthIndex(): Promise<HealthIndexOut> {
    return request<HealthIndexOut>("/health-index/latest");
  },
  async getHealthIndexHistory(): Promise<HealthIndexOut[]> {
    return request<HealthIndexOut[]>("/health-index/history");
  },
  async generateForecast(horizonDays = 7): Promise<ForecastOut> {
    return request<ForecastOut>("/forecast", {
      method: "POST", body: JSON.stringify({ horizon_days: horizonDays }),
    });
  },
  async runWhatIf(changedFactors: Array<{ factor: string; direction: "improve" | "worsen"; magnitude: number }>, baseForecastId?: string): Promise<unknown> {
    return request<unknown>("/what-if", {
      method: "POST",
      body: JSON.stringify({ changed_factors: changedFactors, base_forecast_id: baseForecastId ?? null }),
    });
  },
};

// ─── Assistant ────────────────────────────────────────────────────────────────

export interface ConversationOut {
  id: string;
  title: string | null;
  last_message_at: string | null;
  created_at: string;
  messages?: MessageOut[];
}

export interface MessageOut {
  id: string;
  role: "user" | "assistant";
  content: string;
  confidence: number | null;
  evidence_source_ids: string[];
  self_check_passed: boolean | null;
  escalation_flag: boolean;
  model_version: string | null;
  created_at: string;
}

export const assistantApi = {
  async createConversation(title?: string): Promise<ConversationOut> {
    return request<ConversationOut>("/assistant/conversations", {
      method: "POST", body: JSON.stringify({ title: title ?? null }),
    });
  },
  async listConversations(): Promise<ConversationOut[]> {
    return request<ConversationOut[]>("/assistant/conversations");
  },
  async getConversation(id: string): Promise<ConversationOut> {
    return request<ConversationOut>(`/assistant/conversations/${id}`);
  },
  async sendMessage(conversationId: string, content: string): Promise<MessageOut> {
    return request<MessageOut>(`/assistant/conversations/${conversationId}/messages`, {
      method: "POST", body: JSON.stringify({ content }),
    });
  },
};

// ─── Evidence ─────────────────────────────────────────────────────────────────

export interface EvidenceOut {
  id: string;
  title: string;
  authors: string[];
  journal: string | null;
  publication_year: number | null;
  doi: string | null;
  source_url: string;
  abstract_summary: string;
  topic_tags: string[];
  trust_label: string;
}

export const evidenceApi = {
  async search(query: string): Promise<EvidenceOut[]> {
    return request<EvidenceOut[]>(`/evidence/search?q=${encodeURIComponent(query)}`);
  },
  async get(id: string): Promise<EvidenceOut> {
    return request<EvidenceOut>(`/evidence/${id}`);
  },
};

// ─── Intelligence ─────────────────────────────────────────────────────────────

export const intelligenceApi = {
  async getStatus(): Promise<{
    tier: string; total_inferences: number; active_models: number;
    events_last_24h: number; last_activity_at: string | null; is_idle: boolean;
  }> {
    return request("/intelligence/status");
  },
  async getEvents(): Promise<Array<{ id: string; event_type: string; detail: unknown; occurred_at: string }>> {
    return request("/intelligence/events");
  },
};

// ─── Network ──────────────────────────────────────────────────────────────────

export const networkApi = {
  async getStatus(): Promise<{
    you_are_participating_research: boolean;
    you_are_participating_federated_learning: boolean;
    active_research_participants: number;
    total_accounts: number;
    data_sharing_policy: string;
  }> {
    return request("/network/status");
  },
  async setConsent(consentType: string, granted: boolean): Promise<void> {
    await request("/network/consent", {
      method: "POST", body: JSON.stringify({ consent_type: consentType, granted }),
    });
  },
};

// ─── Reports ──────────────────────────────────────────────────────────────────

export const reportsApi = {
  async exportJson(): Promise<unknown> {
    return request("/reports/export.json");
  },
};
