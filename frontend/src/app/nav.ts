import {
  Bell,
  FlaskConical,
  GitCompareArrows,
  History,
  LayoutDashboard,
  ListChecks,
  ScanSearch,
  Server,
  Settings,
  Users,
  type LucideIcon,
} from "lucide-react";

import { hasRole, type Role, type SessionUser } from "../store/session";

export interface NavEntry {
  to: string;
  label: string;
  icon: LucideIcon;
  minRole: Role;
  /** Match the path exactly (Overview). */
  end?: boolean;
  /** Shown in the mobile bottom bar; everything else goes into "More" (06 §5). */
  mobile?: boolean;
}

export const primaryNav: NavEntry[] = [
  { to: "/", label: "Overview", icon: LayoutDashboard, minRole: "viewer", end: true, mobile: true },
  { to: "/findings", label: "Findings", icon: ScanSearch, minRole: "viewer", mobile: true },
  { to: "/entities", label: "Customers", icon: Users, minRole: "viewer", mobile: true },
  { to: "/investigations", label: "Investigations", icon: History, minRole: "viewer" },
  { to: "/review", label: "Link review", icon: GitCompareArrows, minRole: "analyst" },
  { to: "/alerts", label: "Alerts", icon: Bell, minRole: "viewer", mobile: true },
];

export const adminNav: NavEntry[] = [
  { to: "/rules", label: "Rules", icon: ListChecks, minRole: "admin" },
  { to: "/systems", label: "Systems", icon: Server, minRole: "admin" },
  { to: "/simulation", label: "Simulation", icon: FlaskConical, minRole: "admin" },
];

export const settingsNav: NavEntry = { to: "/settings", label: "Settings", icon: Settings, minRole: "viewer" };

export function visibleEntries(entries: NavEntry[], user: SessionUser | null): NavEntry[] {
  return entries.filter((entry) => hasRole(user, entry.minRole));
}
