/** Where to go after signing in: a same-site path only, never another origin (`//x`, `/\x`). */
export function safeNext(raw: string | null): string {
  if (!raw || !raw.startsWith("/") || raw.startsWith("//") || raw.startsWith("/\\")) return "/";
  if (raw === "/login" || raw.startsWith("/login?") || raw.startsWith("/login/")) return "/";
  return raw;
}

/** `/login`, carrying the page the user wanted so sign-in can return them to it. */
export function loginPath(from: string): string {
  return from === "/" ? "/login" : `/login?next=${encodeURIComponent(from)}`;
}
