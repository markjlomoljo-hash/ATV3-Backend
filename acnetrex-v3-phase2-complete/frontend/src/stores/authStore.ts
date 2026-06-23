/**
 * Auth store - single source of truth for authentication state in the UI.
 *
 * Backed by the real backend API, not localStorage. localStorage is used
 * only for token persistence between page loads (reading the token to check
 * if the user is still authenticated, writing on login, clearing on logout).
 * The user object itself comes from the API /auth/me on each app load.
 */
import { create } from "zustand";
import { authApi, type UserOut } from "@/lib/api/client";

interface AuthState {
  user: UserOut | null;
  onboardingCompleted: boolean;
  isLoading: boolean;
  error: string | null;

  initialize: () => Promise<void>;
  signup: (email: string, password: string, displayName: string) => Promise<void>;
  login: (email: string, password: string, rememberMe?: boolean) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  onboardingCompleted: false,
  isLoading: true,
  error: null,

  initialize: async () => {
    set({ isLoading: true });
    if (!authApi.isAuthenticated()) {
      set({ user: null, isLoading: false });
      return;
    }
    try {
      const user = await authApi.me();
      set({ user, isLoading: false });
    } catch {
      set({ user: null, isLoading: false });
    }
  },

  signup: async (email, password, displayName) => {
    set({ isLoading: true, error: null });
    try {
      const data = await authApi.signup(email, password, displayName);
      set({ user: data.user, onboardingCompleted: data.onboarding_completed, isLoading: false });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Signup failed.";
      set({ error: msg, isLoading: false });
      throw err;
    }
  },

  login: async (email, password, rememberMe = false) => {
    set({ isLoading: true, error: null });
    try {
      const data = await authApi.login(email, password, rememberMe);
      set({ user: data.user, onboardingCompleted: data.onboarding_completed, isLoading: false });
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Login failed.";
      set({ error: msg, isLoading: false });
      throw err;
    }
  },

  logout: async () => {
    try {
      await authApi.logout();
    } finally {
      set({ user: null, onboardingCompleted: false });
    }
  },

  clearError: () => set({ error: null }),
}));
