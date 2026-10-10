import type { Config } from "tailwindcss";

// Every value maps to a token in src/styles/tokens.css (06 §2–§4, §8). No raw colors in components.
const tint = (name: string) => ({ bg: `var(--${name}-bg)`, fg: `var(--${name}-fg)` });

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "var(--ink-950)",
          900: "var(--ink-900)",
          700: "var(--ink-700)",
          500: "var(--ink-500)",
          400: "var(--ink-400)",
          200: "var(--ink-200)",
          100: "var(--ink-100)",
        },
        paper: "var(--paper)",
        "on-dark": { DEFAULT: "var(--on-dark)", muted: "var(--on-dark-muted)" },
        moss: { 500: "var(--moss-500)", 600: "var(--moss-600)", ...tint("moss") },
        peach: tint("peach"),
        rose: tint("rose"),
        amber: tint("amber"),
        indigo: tint("indigo"),
        sky: tint("sky"),
        neutral: tint("neutral"),
      },
      fontFamily: {
        sans: ['"Inter Variable"', "ui-sans-serif", "system-ui", "-apple-system", '"Segoe UI"', "sans-serif"],
      },
      fontSize: {
        display: ["44px", { lineHeight: "48px", letterSpacing: "-0.035em", fontWeight: "500" }],
        kpi: ["36px", { lineHeight: "40px", letterSpacing: "-0.025em", fontWeight: "500" }],
        h2: ["20px", { lineHeight: "28px", letterSpacing: "-0.01em", fontWeight: "600" }],
        h3: ["15px", { lineHeight: "22px", fontWeight: "600" }],
        body: ["14px", { lineHeight: "20px" }],
        small: ["13px", { lineHeight: "18px" }],
        caption: ["12px", { lineHeight: "16px", letterSpacing: "0.005em", fontWeight: "500" }],
      },
      borderRadius: {
        panel: "var(--r-panel)",
        card: "var(--r-card)",
        control: "var(--r-control)",
        pill: "999px",
      },
      boxShadow: {
        card: "var(--shadow-card)",
        raised: "var(--shadow-raised)",
        panel: "var(--shadow-panel)",
        button: "var(--shadow-button)",
      },
      transitionTimingFunction: {
        out: "var(--ease-out)",
        "in-out": "var(--ease-in-out)",
        drawer: "var(--ease-drawer)",
      },
      transitionDuration: {
        press: "var(--dur-press)",
        fast: "var(--dur-fast)",
        base: "var(--dur-base)",
        slow: "var(--dur-slow)",
      },
      maxWidth: { content: "1360px" },
      screens: { pointer: { raw: "(hover: hover) and (pointer: fine)" } },
    },
  },
  plugins: [],
} satisfies Config;
