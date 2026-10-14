import { useSession, type Role, type SessionUser } from "../../store/session";
import { ApiError, apiFetch, setAuthHandlers } from "./client";

/** `user` inside the login/refresh response (04 §2). */
interface TokenUserDto {
  id: string;
  email: string;
  full_name: string;
  role: Role;
}

interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  expires_in: number;
  user: TokenUserDto;
}

function toSessionUser(dto: TokenUserDto): SessionUser {
  return { id: dto.id, email: dto.email, fullName: dto.full_name, role: dto.role };
}

function applyTokens(tokens: TokenResponse): string {
  useSession.getState().setSession(toSessionUser(tokens.user), tokens.access_token);
  return tokens.access_token;
}

export async function signIn(email: string, password: string): Promise<SessionUser> {
  const tokens = await apiFetch<TokenResponse>("/auth/login", {
    method: "POST",
    json: { email, password },
  });
  applyTokens(tokens);
  return toSessionUser(tokens.user);
}

let inFlight: Promise<string | null> | null = null;

/**
 * Exchange the refresh cookie for a new access token. Concurrent callers share one request, because
 * the backend rotates the cookie and treats a second use of the old one as theft (03 §M11).
 *
 * A `401` ends the session. Any other failure (network, 5xx) ends it only during the first check
 * on app load, so a flaky connection does not sign someone out mid-task.
 */
export function refreshAccessToken(): Promise<string | null> {
  inFlight ??= (async () => {
    try {
      return applyTokens(await apiFetch<TokenResponse>("/auth/refresh", { method: "POST" }));
    } catch (error) {
      const session = useSession.getState();
      const rejected = error instanceof ApiError && error.status === 401;
      if (rejected || session.status === "unknown") session.clear();
      return null;
    } finally {
      inFlight = null;
    }
  })();
  return inFlight;
}

/** Revoke the refresh-token family on the server (best effort), then forget the session locally. */
export async function signOut(): Promise<void> {
  const session = useSession.getState();
  if (!session.isDemo && session.accessToken) {
    try {
      await apiFetch<void>("/auth/logout", { method: "POST" });
    } catch (error) {
      // An expired access token: renew once so the server still revokes the refresh family.
      if (error instanceof ApiError && error.status === 401 && (await refreshAccessToken())) {
        await apiFetch<void>("/auth/logout", { method: "POST" }).catch(() => undefined);
      }
      // Otherwise the local session is cleared anyway; an unreachable server must not trap the user.
    }
  }
  useSession.getState().clear();
}

setAuthHandlers({
  getAccessToken: () => useSession.getState().accessToken,
  refreshAccessToken,
});
