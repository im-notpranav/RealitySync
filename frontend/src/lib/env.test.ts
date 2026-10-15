import { describe, expect, it } from "vitest";

import { readEnv } from "./env";

describe("readEnv demo data", () => {
  it("is on in development unless VITE_DEMO_DATA=off", () => {
    expect(readEnv({ DEV: true })).toMatchObject({ demoData: true, demoOnly: false });
    expect(readEnv({ DEV: true, VITE_DEMO_DATA: "off" })).toMatchObject({ demoData: false });
  });

  it("is never on in a production build by default", () => {
    expect(readEnv({ DEV: false })).toMatchObject({ demoData: false, demoOnly: false, isDevelopment: false });
    expect(readEnv({ DEV: false, VITE_DEMO_DATA: "yes" })).toMatchObject({ demoData: false });
  });

  it("turns a production build into a public demo with VITE_DEMO_DATA=on", () => {
    expect(readEnv({ DEV: false, VITE_DEMO_DATA: "on" })).toMatchObject({
      demoData: true,
      demoOnly: true,
      isDevelopment: false,
    });
  });

  it("trims trailing slashes from the API origin", () => {
    expect(readEnv({ DEV: false, VITE_API_BASE_URL: "https://api.example.test//" }).apiBaseUrl).toBe(
      "https://api.example.test",
    );
  });
});
