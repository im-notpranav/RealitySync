import { create } from "zustand";

export type Role = "viewer" | "analyst" | "admin";

export interface SessionUser {
  id: string;
  email: string;
  fullName: string;
  role: Role;
}

/** `unknown` until the first silent refresh on app load has answered. */
export type SessionStatus = "unknown" | "authenticated" | "anonymous";

const roleRank: Record<Role, number> = { viewer: 0, analyst: 1, admin: 2 };

export function hasRole(user: SessionUser | null, minimum: Role): boolean {
  return user !== null && roleRank[user.role] >= roleRank[minimum];
}

interface SessionState {
  status: SessionStatus;
  user: SessionUser | null;
  /** Access token lives in memory only (02 §5); never persisted. */
  accessToken: string | null;
  /** Development-only session that browses demo data without a backend (D-049). */
  isDemo: boolean;
  setSession: (user: SessionUser, accessToken: string) => void;
  startDemo: (user: SessionUser) => void;
  clear: () => void;
}

export const useSession = create<SessionState>((set) => ({
  status: "unknown",
  user: null,
  accessToken: null,
  isDemo: false,
  setSession: (user, accessToken) => set({ status: "authenticated", user, accessToken, isDemo: false }),
  startDemo: (user) => set({ status: "authenticated", user, accessToken: null, isDemo: true }),
  clear: () => set({ status: "anonymous", user: null, accessToken: null, isDemo: false }),
}));
