import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Minimal typing for the Node global (no @types/node dependency).
declare const process: { env: Record<string, string | undefined> };

export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    // Bind mounts on Docker Desktop (Windows/macOS) don't forward file events; poll instead.
    watch: process.env.VITE_WATCH_POLLING === "true" ? { usePolling: true, interval: 300 } : undefined,
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    restoreMocks: true,
    // Above the 5 s findBy timeout in src/test/setup.ts, so a slow lazy page import fails as a
    // missing element, not a test timeout.
    testTimeout: 15_000,
  },
});
