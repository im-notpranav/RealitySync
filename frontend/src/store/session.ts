import { create } from "zustand";

import { env } from "../lib/env";

export type Role = "viewer" | "analyst" | "admin";

export interface SessionUser {
  id: string;
  fullName: string;
  role: Role;
}

const roleRank: Record<Role, number> = { viewer: 0, analyst: 1, admin: 2 };

export function hasRole(user: SessionUser | null, minimum: Role): boolean {
  return user !== null && roleRank[user.role] >= roleRank[minimum];
}

interface SessionState {
  user: SessionUser | null;
  /** Access token lives in memory only (02 §5); never persisted. */
  accessToken: string | null;
  setSession: (user: SessionUser, accessToken: string) => void;
  clear: () => void;
}

// TODO(T-008): replace with the real login flow. Until then development builds get a local demo admin
// so the shell and role-gated navigation can be exercised; production builds start signed out.
const devUser: SessionUser | null = env.isDevelopment
  ? { id: "dev-admin", fullName: "Demo Admin", role: "admin" }
  : null;

export const useSession = create<SessionState>((set) => ({
  user: devUser,
  accessToken: null,
  setSession: (user, accessToken) => set({ user, accessToken }),
  clear: () => set({ user: null, accessToken: null }),
}));
