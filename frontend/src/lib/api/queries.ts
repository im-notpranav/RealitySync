import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { env } from "../env";
import * as demo from "../demo/data";
import { apiFetch } from "./client";
import type {
  Alert,
  AsOfView,
  AuditItem,
  Checkpoint,
  DashboardSummary,
  EntityDetail,
  EntityListItem,
  Evaluation,
  FailedEvent,
  FindingDetail,
  FindingListItem,
  FindingStatus,
  Investigation,
  LinkReviewItem,
  Rule,
  SimulationRun,
  SourceSystem,
  SystemHealth,
  TimelineItem,
  TrendPoint,
  UserItem,
} from "./types";

/**
 * Query hooks for every screen. In development the backend endpoints do not exist yet, so `env.demoData`
 * serves the synthetic data in `lib/demo` with a short latency (skeletons stay visible). Feature tasks
 * flip each hook to the real endpoint by removing its demo branch (D-049).
 */
const LATENCY = 260;

function fromDemo<T>(value: () => T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(structuredClone(value())), LATENCY));
}

function load<T>(path: string, demoValue: () => T): Promise<T> {
  return env.demoData ? fromDemo(demoValue) : apiFetch<T>(path);
}

interface Page<T> {
  items: T[];
}

function loadItems<T>(path: string, demoValue: () => T[]): Promise<T[]> {
  return env.demoData ? fromDemo(demoValue) : apiFetch<Page<T>>(path).then((page) => page.items);
}

// -------------------------------------------------------------------- overview

export const useDashboardSummary = () =>
  useQuery({
    queryKey: ["dashboard", "summary"],
    queryFn: () => load<DashboardSummary>("/dashboard/summary", () => demo.dashboardSummary),
  });

export const useTrends = () =>
  useQuery({
    queryKey: ["dashboard", "trends", "7d"],
    queryFn: () =>
      env.demoData
        ? fromDemo(() => demo.trends)
        : apiFetch<{ points: TrendPoint[] }>("/dashboard/trends?range=7d").then((r) => r.points),
  });

export const useSystemHealth = () =>
  useQuery({
    queryKey: ["systems", "health"],
    queryFn: () => load<SystemHealth[]>("/source-systems", () => demo.systemHealth),
  });

// -------------------------------------------------------------------- findings

export interface FindingFilters {
  q?: string;
  status?: FindingStatus | "active" | "all";
  severity?: string;
  system?: string;
}

function matchesFilters(finding: FindingListItem, filters: FindingFilters): boolean {
  const status = filters.status ?? "active";
  if (status === "active" && !["open", "acknowledged"].includes(finding.status)) return false;
  if (status !== "active" && status !== "all" && finding.status !== status) return false;
  if (filters.severity && filters.severity !== "all" && finding.severity !== filters.severity) return false;
  if (filters.system && filters.system !== "all" && !finding.systems.includes(filters.system as never))
    return false;
  if (filters.q) {
    const q = filters.q.toLowerCase();
    if (!`${finding.title} ${finding.entity_name} ${finding.rule_key}`.toLowerCase().includes(q))
      return false;
  }
  return true;
}

export const useFindings = (filters: FindingFilters = {}) =>
  useQuery({
    queryKey: ["findings", filters],
    queryFn: () =>
      loadItems<FindingListItem>(`/findings?${new URLSearchParams(filters as Record<string, string>)}`, () =>
        demo.findings
          .filter((f) => matchesFilters(f, filters))
          .sort((a, b) => b.priority_score - a.priority_score),
      ),
  });

export const useFinding = (id: string | null) =>
  useQuery({
    queryKey: ["finding", id],
    enabled: Boolean(id),
    queryFn: () => load<FindingDetail>(`/findings/${id}`, () => demo.findingDetails[id!]!),
  });

export function useUpdateFindingStatus() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, status, note }: { id: string; status: FindingStatus; note?: string }) => {
      if (!env.demoData)
        return apiFetch<FindingDetail>(`/findings/${id}`, { method: "PATCH", json: { status, note } });
      const detail = demo.findingDetails[id]!;
      const listItem = demo.findings.find((f) => f.id === id)!;
      detail.status = status;
      listItem.status = status;
      detail.history.push({ at: new Date().toISOString(), action: status, by: "Demo Admin", note });
      return fromDemo(() => detail);
    },
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["findings"] });
      void client.invalidateQueries({ queryKey: ["finding"] });
    },
  });
}

// -------------------------------------------------------------------- customers

export const useEntities = (q = "") =>
  useQuery({
    queryKey: ["entities", q],
    queryFn: () =>
      loadItems<EntityListItem>(`/entities?q=${encodeURIComponent(q)}`, () =>
        demo.entities.filter((e) =>
          `${e.canonical_name} ${e.canonical_email}`.toLowerCase().includes(q.toLowerCase()),
        ),
      ),
  });

export const useEntity = (id: string) =>
  useQuery({
    queryKey: ["entity", id],
    queryFn: () => load<EntityDetail | null>(`/entities/${id}`, () => demo.entityDetail(id)),
  });

export const useEntityTimeline = (id: string) =>
  useQuery({
    queryKey: ["entity", id, "timeline"],
    queryFn: () => loadItems<TimelineItem>(`/entities/${id}/timeline`, () => demo.entityTimeline(id)),
  });

export const useAsOf = (id: string, at: string | null) =>
  useQuery({
    queryKey: ["entity", id, "as-of", at],
    enabled: Boolean(at),
    placeholderData: (previous) => previous,
    queryFn: () =>
      load<AsOfView | null>(`/entities/${id}/as-of?at=${encodeURIComponent(at!)}`, () =>
        demo.asOfView(id, at!),
      ),
  });

// -------------------------------------------------------------------- alerts, links

export const useAlerts = () =>
  useQuery({ queryKey: ["alerts"], queryFn: () => loadItems<Alert>("/alerts", () => demo.alerts) });

export const useLinkQueue = () =>
  useQuery({
    queryKey: ["links", "needs_review"],
    queryFn: () => loadItems<LinkReviewItem>("/links?status=needs_review", () => demo.linkQueue),
  });

export function useDecideLink() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: async ({ id, decision }: { id: string; decision: "confirm" | "reject" }) => {
      if (!env.demoData) return apiFetch(`/links/${id}/${decision}`, { method: "POST", json: {} });
      const index = demo.linkQueue.findIndex((l) => l.id === id);
      if (index >= 0) demo.linkQueue.splice(index, 1);
      return fromDemo(() => null);
    },
    onSuccess: () => void client.invalidateQueries({ queryKey: ["links"] }),
  });
}

// -------------------------------------------------------------------- investigations

export const useInvestigations = () =>
  useQuery({
    queryKey: ["investigations"],
    queryFn: () => loadItems<Investigation>("/investigations", () => demo.investigations),
  });

export const useInvestigation = (id: string) =>
  useQuery({
    queryKey: ["investigation", id],
    queryFn: () =>
      load<Investigation | null>(
        `/investigations/${id}`,
        () => demo.investigations.find((i) => i.id === id) ?? null,
      ),
  });

export const useCheckpoints = (id: string) =>
  useQuery({
    queryKey: ["investigation", id, "checkpoints"],
    queryFn: () => loadItems<Checkpoint>(`/investigations/${id}/checkpoints`, () => demo.checkpoints(id)),
  });

// -------------------------------------------------------------------- admin

export const useRules = () =>
  useQuery({ queryKey: ["rules"], queryFn: () => loadItems<Rule>("/rules", () => demo.rules) });

export const useSourceSystems = () =>
  useQuery({
    queryKey: ["source-systems"],
    queryFn: () => loadItems<SourceSystem>("/source-systems", () => demo.sourceSystems),
  });

export const useFailedEvents = () =>
  useQuery({
    queryKey: ["ingest", "failed"],
    queryFn: () => loadItems<FailedEvent>("/ingest/events?status=failed", () => demo.failedEvents),
  });

export const useSimulationRuns = () =>
  useQuery({
    queryKey: ["simulation", "runs"],
    queryFn: () => loadItems<SimulationRun>("/simulation/runs", () => demo.simulationRuns),
  });

export const useEvaluation = (runId: string) =>
  useQuery({
    queryKey: ["simulation", runId, "evaluation"],
    queryFn: () => load<Evaluation>(`/simulation/runs/${runId}/evaluation`, () => demo.evaluation),
  });

export const useUsers = () =>
  useQuery({ queryKey: ["users"], queryFn: () => loadItems<UserItem>("/users", () => demo.users) });

export const useAuditLog = () =>
  useQuery({ queryKey: ["audit"], queryFn: () => loadItems<AuditItem>("/audit-logs", () => demo.auditLog) });
