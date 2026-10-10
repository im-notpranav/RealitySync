import type { RouteObject } from "react-router-dom";

import { env } from "../lib/env";
import type { Role } from "../store/session";
import { AppShell } from "./shell/AppShell";

/** Route metadata read by placeholder pages until each feature task replaces its page. */
export interface RouteHandle {
  title: string;
  subtitle: string;
  task: string;
  minRole?: Role;
}

const placeholder = (handle: RouteHandle): Pick<RouteObject, "handle" | "lazy"> => ({
  handle,
  lazy: () => import("../pages/PlaceholderPage"),
});

/** Opt into React Router v7 behaviour now so the later upgrade is a no-op. */
export const routerFuture = {
  v7_fetcherPersist: true,
  v7_normalizeFormMethod: true,
  v7_partialHydration: true,
  v7_relativeSplatPath: true,
  v7_skipActionErrorRevalidation: true,
} as const;

/** Every route in 02 §3.1, lazy-loaded. */
export const routes: RouteObject[] = [
  { path: "/login", lazy: () => import("../pages/LoginPage") },
  {
    path: "/",
    element: <AppShell />,
    children: [
      {
        index: true,
        ...placeholder({
          title: "Overview",
          subtitle: "Live consistency across CRM, Billing and Support",
          task: "T-031",
        }),
      },
      {
        path: "findings",
        ...placeholder({
          title: "Findings",
          subtitle: "Contradictions between your systems, ranked by priority",
          task: "T-033",
        }),
      },
      {
        path: "entities",
        ...placeholder({
          title: "Customers",
          subtitle: "Every customer as your systems describe them",
          task: "T-034",
        }),
      },
      {
        path: "entities/:id",
        ...placeholder({
          title: "Customer",
          subtitle: "Records, findings, risk and history for one customer",
          task: "T-034 and T-059",
        }),
      },
      {
        path: "investigations",
        ...placeholder({
          title: "Investigations",
          subtitle: "Could RealitySync have known earlier?",
          task: "T-059",
        }),
      },
      {
        path: "investigations/:id",
        ...placeholder({
          title: "Investigation",
          subtitle: "What was knowable before the incident",
          task: "T-059",
        }),
      },
      {
        path: "review",
        ...placeholder({
          title: "Link review",
          subtitle: "Confirm or reject uncertain customer matches",
          task: "T-038",
          minRole: "analyst",
        }),
      },
      {
        path: "alerts",
        ...placeholder({ title: "Alerts", subtitle: "Everything RealitySync flagged, newest first", task: "T-035" }),
      },
      {
        path: "rules",
        ...placeholder({
          title: "Rules",
          subtitle: "Detection rules, severities and settings",
          task: "T-037",
          minRole: "admin",
        }),
      },
      {
        path: "systems",
        ...placeholder({
          title: "Systems",
          subtitle: "Source systems, field authority and failed events",
          task: "T-037",
          minRole: "admin",
        }),
      },
      {
        path: "simulation",
        ...placeholder({
          title: "Simulation",
          subtitle: "Generate synthetic CRM, Billing and Support data",
          task: "T-036",
          minRole: "admin",
        }),
      },
      {
        path: "simulation/:runId/evaluation",
        ...placeholder({
          title: "Evaluation",
          subtitle: "How well RealitySync found what was injected",
          task: "T-036",
          minRole: "admin",
        }),
      },
      {
        path: "settings",
        ...placeholder({ title: "Settings", subtitle: "Profile, users, API keys and audit log", task: "T-049" }),
      },
      ...(env.isDevelopment ? [{ path: "styleguide", lazy: () => import("../pages/StyleguidePage") }] : []),
      { path: "*", lazy: () => import("../pages/NotFoundPage") },
    ],
  },
];
