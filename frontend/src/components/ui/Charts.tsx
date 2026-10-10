import { useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import type { Checkpoint, RiskAssessment, RiskSignalName, TrendPoint } from "../../lib/api/types";
import { cn } from "../../lib/cn";
import { formatShortDate } from "../../lib/format";

interface TooltipPayload {
  active?: boolean;
  label?: string | number;
  payload?: ReadonlyArray<{
    name?: string;
    value?: number | string;
    color?: string;
    dataKey?: string | number;
  }>;
}

function ChartTooltip({
  active,
  label,
  payload,
  labelFormat,
}: TooltipPayload & { labelFormat: (label: string) => string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-[8px] bg-ink-950 px-2.5 py-2 text-caption text-on-dark shadow-raised">
      <p className="mb-1 text-on-dark-muted">{labelFormat(String(label))}</p>
      {payload.map((entry) => (
        <p key={String(entry.dataKey)} className="flex items-center gap-2 tabular">
          <span aria-hidden="true" className="size-2 rounded-pill" style={{ background: entry.color }} />
          {entry.name}: {typeof entry.value === "number" ? Number(entry.value.toFixed(3)) : entry.value}
        </p>
      ))}
    </div>
  );
}

const axis = { fontSize: 12, fill: "var(--ink-500)" };
const weekday = (iso: string) => new Intl.DateTimeFormat("en-GB", { weekday: "short" }).format(new Date(iso));

/** Created vs resolved per day (06 §7.1 "Findings this week"). */
export function TrendChart({ points, animate }: { points: TrendPoint[]; animate: boolean }) {
  return (
    <div className="h-[220px] w-full">
      <ResponsiveContainer>
        <BarChart data={points} barGap={4} margin={{ top: 8, right: 4, bottom: 0, left: 0 }}>
          <CartesianGrid vertical={false} stroke="var(--ink-100)" />
          <XAxis dataKey="date" tickFormatter={weekday} tickLine={false} axisLine={false} tick={axis} />
          <YAxis allowDecimals={false} tickLine={false} axisLine={false} tick={axis} width={28} />
          <Tooltip
            cursor={{ fill: "var(--ink-100)" }}
            content={(props) => (
              <ChartTooltip {...(props as unknown as TooltipPayload)} labelFormat={formatShortDate} />
            )}
          />
          <Bar
            dataKey="created"
            name="Created"
            fill="var(--ink-950)"
            radius={[6, 6, 2, 2]}
            maxBarSize={18}
            isAnimationActive={animate}
            animationDuration={600}
          />
          <Bar
            dataKey="resolved"
            name="Resolved"
            fill="var(--moss-500)"
            radius={[6, 6, 2, 2]}
            maxBarSize={18}
            isAnimationActive={animate}
            animationDuration={600}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

/**
 * Investigation replay: risk score per checkpoint, the warning threshold and the crossing point
 * (06 §7.8). The line draws left → right once (900 ms, ease-in-out).
 */
export function ReplayChart({
  checkpoints,
  threshold,
  crossingAt,
  animate,
}: {
  checkpoints: Checkpoint[];
  threshold: number;
  crossingAt: string | null;
  animate: boolean;
}) {
  const crossing = crossingAt
    ? checkpoints.find((c) => new Date(c.at).getTime() >= new Date(crossingAt).getTime())
    : undefined;
  // The crossing dot appears once the line has finished drawing (06 §8).
  const [showDot, setShowDot] = useState(!animate);
  useEffect(() => {
    if (!animate) return;
    const timer = window.setTimeout(() => setShowDot(true), 900);
    return () => window.clearTimeout(timer);
  }, [animate]);
  return (
    <div className="h-[260px] w-full">
      <ResponsiveContainer>
        <AreaChart data={checkpoints} margin={{ top: 16, right: 12, bottom: 0, left: 0 }}>
          <defs>
            <linearGradient id="replay-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--ink-950)" stopOpacity={0.14} />
              <stop offset="100%" stopColor="var(--ink-950)" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid vertical={false} stroke="var(--ink-100)" />
          <XAxis
            dataKey="at"
            tickFormatter={formatShortDate}
            tickLine={false}
            axisLine={false}
            tick={axis}
            minTickGap={48}
          />
          <YAxis
            domain={[0, 1]}
            ticks={[0, 0.4, 0.6, 0.8, 1]}
            tickLine={false}
            axisLine={false}
            tick={axis}
            width={32}
            tickFormatter={(v: number) => v.toFixed(1)}
          />
          <Tooltip
            cursor={{ stroke: "var(--ink-400)", strokeDasharray: "3 3" }}
            content={(props) => (
              <ChartTooltip {...(props as unknown as TooltipPayload)} labelFormat={formatShortDate} />
            )}
          />
          <ReferenceLine
            y={threshold}
            stroke="var(--peach-fg)"
            strokeDasharray="4 4"
            label={{
              value: `Warning ${threshold.toFixed(2)}`,
              position: "insideTopLeft",
              fill: "var(--peach-fg)",
              fontSize: 12,
            }}
          />
          <Area
            type="monotone"
            dataKey="risk_score"
            name="Risk"
            stroke="var(--ink-950)"
            strokeWidth={2}
            fill="url(#replay-fill)"
            dot={false}
            activeDot={{ r: 4, fill: "var(--ink-950)", stroke: "var(--paper)", strokeWidth: 2 }}
            isAnimationActive={animate}
            animationDuration={900}
            animationEasing="ease-in-out"
          />
          {crossing && showDot ? (
            <ReferenceDot
              x={crossing.at}
              y={crossing.risk_score}
              r={6}
              fill="var(--peach-fg)"
              stroke="var(--paper)"
              strokeWidth={2}
            />
          ) : null}
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

const signalLabels: Record<RiskSignalName, string> = {
  payment_delay: "Payment delay",
  complaint_trend: "Complaint trend",
  commercial_decline: "Commercial decline",
  open_inconsistencies: "Open inconsistencies",
};

/** The four risk signals with their weights (03 §M12). Unavailable signals say so instead of showing 0. */
export function SignalBars({ risk }: { risk: RiskAssessment }) {
  return (
    <ul className="flex flex-col gap-3">
      {(Object.keys(signalLabels) as RiskSignalName[]).map((name) => {
        const signal = risk.signals[name];
        return (
          <li key={name} className="grid grid-cols-[1fr_auto] items-center gap-x-3 gap-y-1.5">
            <span className="text-small text-ink-900">
              {signalLabels[name]} <span className="text-ink-500">· weight {signal.weight.toFixed(2)}</span>
            </span>
            <span className="text-small font-medium tabular text-ink-900">
              {signal.available ? signal.value.toFixed(2) : "No data"}
            </span>
            <span className="col-span-2 h-1.5 overflow-hidden rounded-pill bg-ink-200">
              <span
                className={cn(
                  "block h-full rounded-pill",
                  signal.available ? "bg-ink-950" : "bg-transparent",
                )}
                style={{ width: `${signal.available ? signal.value * 100 : 0}%` }}
              />
            </span>
          </li>
        );
      })}
    </ul>
  );
}
