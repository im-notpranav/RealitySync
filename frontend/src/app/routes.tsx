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
      { index: true, lazy: () => import("../features/dashboard/OverviewPage") },
      { path: "findings", lazy: () => import("../features/findings/FindingsPage") },
      { path: "entities", lazy: () => import("../features/entities/CustomersPage") },
      { path: "entities/:id", lazy: () => import("../features/entities/CustomerPage") },
      { path: "investigations", lazy: () => import("../features/investigations/InvestigationsPage") },
      { path: "investigations/:id", lazy: () => import("../features/investigations/InvestigationPage") },
      { path: "review", lazy: () => import("../features/links/LinkReviewPage") },
      { path: "alerts", lazy: () => import("../features/alerts/AlertsPage") },
      { path: "rules", lazy: () => import("../features/admin/RulesPage") },
      { path: "systems", lazy: () => import("../features/admin/SystemsPage") },
      { path: "simulation", lazy: () => import("../features/admin/SimulationPage") },
      { path: "simulation/:runId/evaluation", lazy: () => import("../features/admin/EvaluationPage") },
      { path: "settings", lazy: () => import("../features/settings/SettingsPage") },
      ...(env.isDevelopment ? [{ path: "styleguide", lazy: () => import("../pages/StyleguidePage") }] : []),
      { path: "*", lazy: () => import("../pages/NotFoundPage") },
    ],
  },
];
