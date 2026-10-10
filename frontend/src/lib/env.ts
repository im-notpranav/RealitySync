export const env = {
  /** Backend origin; empty means same origin. */
  apiBaseUrl: (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/+$/, ""),
  /** `/styleguide` and the dev session exist only in development (02 §3.1). */
  isDevelopment: import.meta.env.DEV || import.meta.env.VITE_APP_ENV === "development",
  /** Serve synthetic demo data until the backend endpoints exist (D-049). `VITE_DEMO_DATA=off` disables it. */
  demoData:
    (import.meta.env.DEV || import.meta.env.VITE_APP_ENV === "development") &&
    import.meta.env.VITE_DEMO_DATA !== "off",
};
