interface BuildEnv {
  DEV: boolean;
  VITE_API_BASE_URL?: string;
  VITE_APP_ENV?: string;
  VITE_DEMO_DATA?: string;
}

export function readEnv(source: BuildEnv) {
  const isDevelopment = source.DEV || source.VITE_APP_ENV === "development";
  /** Public demo build (D-071): synthetic data only, no backend is called. */
  const demoOnly = source.VITE_DEMO_DATA === "on";
  return {
    /** Backend origin; empty means same origin. */
    apiBaseUrl: (source.VITE_API_BASE_URL ?? "").replace(/\/+$/, ""),
    /** `/styleguide` and the dev session exist only in development (02 §3.1). */
    isDevelopment,
    demoOnly,
    /**
     * Serve synthetic demo data until the backend endpoints exist (D-049): on in development unless
     * `VITE_DEMO_DATA=off`, and in production builds only with `VITE_DEMO_DATA=on`.
     */
    demoData: demoOnly || (isDevelopment && source.VITE_DEMO_DATA !== "off"),
  };
}

export const env = readEnv(import.meta.env);
