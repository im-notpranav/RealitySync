import { Contact, Gauge, LifeBuoy, Receipt } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import type { ReactNode } from "react";

import type { ConfidenceBreakdown, FindingStatus, RiskLevel, Severity, SystemKey } from "../../lib/api/types";
import { cn } from "../../lib/cn";
import { formatPercent, systemNames } from "../../lib/format";
import { Tooltip } from "./Overlays";

export type Tone = "peach" | "rose" | "amber" | "indigo" | "sky" | "moss" | "neutral";

const toneClass: Record<Tone, string> = {
  peach: "bg-peach-bg text-peach-fg",
  rose: "bg-rose-bg text-rose-fg",
  amber: "bg-amber-bg text-amber-fg",
  indigo: "bg-indigo-bg text-indigo-fg",
  sky: "bg-sky-bg text-sky-fg",
  moss: "bg-moss-bg text-moss-fg",
  neutral: "bg-neutral-bg text-neutral-fg",
};

export interface PillProps {
  tone?: Tone;
  dot?: boolean;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
  title?: string;
}

/** Soft tinted pill (06 §2.2): background + text of the same hue, always with text. */
export function Pill({ tone = "neutral", dot, icon, children, className, title }: PillProps) {
  return (
    <span
      title={title}
      className={cn(
        "inline-flex h-6 shrink-0 items-center gap-1.5 whitespace-nowrap rounded-pill px-2.5 text-caption",
        toneClass[tone],
        className,
      )}
    >
      {dot ? <span aria-hidden="true" className="size-1.5 rounded-pill bg-current" /> : null}
      {icon}
      {children}
    </span>
  );
}

// ------------------------------------------------------------------ severity

export const severityTone: Record<Severity, Tone> = {
  critical: "rose",
  high: "peach",
  medium: "amber",
  low: "neutral",
};
export const severityLabel: Record<Severity, string> = {
  critical: "Critical",
  high: "High",
  medium: "Medium",
  low: "Low",
};

/** Shape carries meaning without colour (06 §6): ▲ critical, ◆ high, ● medium, ○ low. */
export function SeverityShape({ severity }: { severity: Severity }) {
  return (
    <svg viewBox="0 0 10 10" className="size-2.5 shrink-0" aria-hidden="true">
      {severity === "critical" ? <path d="M5 1 9.2 8.6H.8Z" className="fill-current" /> : null}
      {severity === "high" ? <path d="M5 .8 9.2 5 5 9.2.8 5Z" className="fill-current" /> : null}
      {severity === "medium" ? <circle cx="5" cy="5" r="4" className="fill-current" /> : null}
      {severity === "low" ? (
        <circle cx="5" cy="5" r="3.3" className="fill-none stroke-current" strokeWidth="1.4" />
      ) : null}
    </svg>
  );
}

export function SeverityBadge({ severity, className }: { severity: Severity; className?: string }) {
  return (
    <Pill tone={severityTone[severity]} icon={<SeverityShape severity={severity} />} className={className}>
      {severityLabel[severity]}
    </Pill>
  );
}

// ------------------------------------------------------------------ finding status

const statusStyle: Record<FindingStatus, { label: string; tone: Tone }> = {
  open: { label: "Open", tone: "neutral" },
  acknowledged: { label: "Acknowledged", tone: "sky" },
  resolved: { label: "Resolved", tone: "moss" },
  false_positive: { label: "False positive", tone: "neutral" },
  auto_resolved: { label: "Auto-resolved", tone: "moss" },
};

/** Status changes crossfade with a short blur so the swap reads as one object (06 §8). */
export function StatusPill({ status }: { status: FindingStatus }) {
  const style = statusStyle[status];
  return (
    <span className="relative inline-flex">
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.span
          key={status}
          initial={{ opacity: 0, filter: "blur(2px)" }}
          animate={{ opacity: 1, filter: "blur(0px)" }}
          exit={{ opacity: 0, filter: "blur(2px)" }}
          transition={{ duration: 0.2 }}
        >
          <Pill tone={style.tone} dot={status === "open"}>
            {style.label}
          </Pill>
        </motion.span>
      </AnimatePresence>
    </span>
  );
}

// ------------------------------------------------------------------ systems

const systemIcon = { crm: Contact, billing: Receipt, support: LifeBuoy } as const;

export function SystemChip({ system }: { system: SystemKey }) {
  const Icon = systemIcon[system];
  return (
    <Pill tone="neutral" icon={<Icon size={12} strokeWidth={2} aria-hidden="true" />}>
      {systemNames[system]}
    </Pill>
  );
}

// ------------------------------------------------------------------ risk

export const riskTone: Record<RiskLevel, Tone> = {
  low: "moss",
  watch: "indigo",
  warning: "peach",
  critical: "rose",
};
export const riskLabel: Record<RiskLevel, string> = {
  low: "Low",
  watch: "Watch",
  warning: "Warning",
  critical: "Critical",
};

/** Risk is never shown without its confidence (06 §7.8, FR-RSK-002). */
export function RiskBadge({
  level,
  confidence,
  className,
}: {
  level: RiskLevel;
  confidence: number;
  className?: string;
}) {
  return (
    <span
      aria-label={`Risk ${riskLabel[level]}, confidence ${formatPercent(confidence)}`}
      className="inline-flex"
    >
      <Pill
        tone={riskTone[level]}
        icon={<Gauge size={12} strokeWidth={2} aria-hidden="true" />}
        className={className}
      >
        <span aria-hidden="true">
          {riskLabel[level]} <span className="opacity-70">· {formatPercent(confidence)}</span>
        </span>
      </Pill>
    </span>
  );
}

// ------------------------------------------------------------------ confidence

function ConfidenceRing({ value, size = 20 }: { value: number; size?: number }) {
  const radius = size / 2 - 2.5;
  const circumference = 2 * Math.PI * radius;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true" className="-rotate-90">
      <circle cx={size / 2} cy={size / 2} r={radius} className="fill-none stroke-ink-200" strokeWidth="2.5" />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        className="fill-none stroke-ink-950"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeDasharray={`${circumference * value} ${circumference}`}
      />
    </svg>
  );
}

export function ConfidenceMeter({ value, breakdown }: { value: number; breakdown?: ConfidenceBreakdown }) {
  const meter = (
    <span className="inline-flex items-center gap-1.5 text-small font-medium tabular text-ink-900">
      <ConfidenceRing value={value} />
      {formatPercent(value)}
      <span className="sr-only"> confidence</span>
    </span>
  );
  if (!breakdown) return meter;
  return (
    <Tooltip
      content={
        <dl className="grid grid-cols-[auto_auto] gap-x-4 gap-y-0.5 tabular">
          {(["link", "rule", "evidence", "recency"] as const).map((key) => (
            <div key={key} className="contents">
              <dt className="text-on-dark-muted">{key[0]!.toUpperCase() + key.slice(1)}</dt>
              <dd className="text-right">{breakdown[key].toFixed(2)}</dd>
            </div>
          ))}
        </dl>
      }
    >
      <button
        type="button"
        className="rounded-[6px]"
        aria-label={`Confidence ${formatPercent(value)}, show breakdown`}
      >
        {meter}
      </button>
    </Tooltip>
  );
}
