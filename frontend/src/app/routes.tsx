import type { RouteObject } from "react-router-dom";

import { RequireAuth } from "../features/auth/RequireAuth";
import { RequireRole } from "../features/auth/RequireRole";
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

/** Opt into React Router v7 behaviour now so the later upgrade is a no-op. */
export const routerFuture = {
  v7_fetcherPersist: true,
  v7_normalizeFormMethod: true,
  v7_partialHydration: true,
  v7_relativeSplatPath: true,
  v7_skipActionErrorRevalidation: true,
} as const;

/** A route that needs more than `viewer` (02 §3.1); the guard renders the no-access state instead. */
function guarded(min: Role, title: string, route: RouteObject): RouteObject {
  return { element: <RequireRole min={min} title={title} />, children: [route] };
}

/** Every route in 02 §3.1, lazy-loaded. Everything except `/login` needs a session. */
export const routes: RouteObject[] = [
  { path: "/login", lazy: () => import("../features/auth/LoginPage") },
  {
    element: <RequireAuth />,
    children: [
      {
        path: "/",
        element: <AppShell />,
        children: [
          { index: true, lazy: () => import("../features/dashboard/OverviewPage") },
          { path: "findings", lazy: () => import("../features/findings/FindingsPage") },
          { path: "entities", lazy: () => import("../features/entities/CustomersPage") },
          { path: "entities/:id", lazy: () => import("../features/entities/CustomerPage") },
          { path: "investigations", lazy: () => import("../features/investigations/InvestigationsPage") },
          { path: "investigations/:id", lazy: () => import("../features/investigations/InvestigationPage") },
          guarded("analyst", "Link review", {
            path: "review",
            lazy: () => import("../features/links/LinkReviewPage"),
          }),
          { path: "alerts", lazy: () => import("../features/alerts/AlertsPage") },
          guarded("admin", "Rules", { path: "rules", lazy: () => import("../features/admin/RulesPage") }),
          guarded("admin", "Systems", {
            path: "systems",
            lazy: () => import("../features/admin/SystemsPage"),
          }),
          guarded("admin", "Simulation", {
            path: "simulation",
            lazy: () => import("../features/admin/SimulationPage"),
          }),
          guarded("admin", "Evaluation", {
            path: "simulation/:runId/evaluation",
            lazy: () => import("../features/admin/EvaluationPage"),
          }),
          { path: "settings", lazy: () => import("../features/settings/SettingsPage") },
          ...(env.isDevelopment
            ? [{ path: "styleguide", lazy: () => import("../pages/StyleguidePage") }]
            : []),
          { path: "*", lazy: () => import("../pages/NotFoundPage") },
        ],
      },
    ],
  },
];
