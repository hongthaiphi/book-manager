import { create } from "zustand";
import apiClient from "@/api/client";

export interface AuthUser {
  id: string;
  email: string;
  name: string;
  avatar_url: string | null;
  phone_verified: boolean;
  profile_slug: string | null;
  building_id: string | null;
}

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  isLoading: boolean;
  setTokenAndFetchUser: (token: string) => Promise<void>;
  fetchUser: () => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  accessToken: localStorage.getItem("access_token"),
  isLoading: false,

  setTokenAndFetchUser: async (token: string) => {
    localStorage.setItem("access_token", token);
    set({ accessToken: token });
    await get().fetchUser();
  },

  fetchUser: async () => {
    set({ isLoading: true });
    try {
      const { data } = await apiClient.get<AuthUser>("/auth/me");
      set({ user: data, isLoading: false });
    } catch {
      set({ user: null, accessToken: null, isLoading: false });
      localStorage.removeItem("access_token");
    }
  },

  logout: async () => {
    try {
      await apiClient.post("/auth/logout");
    } finally {
      localStorage.removeItem("access_token");
      set({ user: null, accessToken: null });
    }
  },
}));
