import { ApiError } from "../../lib/api/client";

/** Plain-language sign-in errors (06 copy rules); never reveals whether an account exists. */
export function signInErrorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return "Can't reach RealitySync. Check your connection and try again.";
  if (error.status === 401) return "Email or password is incorrect.";
  if (error.status === 429) {
    const seconds = error.retryAfter ?? 60;
    return `Too many attempts. Try again in ${seconds} second${seconds === 1 ? "" : "s"}.`;
  }
  if (error.status === 422) return "Enter a valid email address and your password.";
  return "Something went wrong. Try again.";
}
