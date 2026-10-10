export const env = {
  /** Backend origin; empty means same origin. */
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, ""),
  /** `/styleguide` and the dev session exist only in development (02 §3.1). */
  isDevelopment: import.meta.env.DEV || import.meta.env.VITE_APP_ENV === "development",
};
