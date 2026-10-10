import { cn } from "../../lib/cn";

/** Two arcs syncing around a centre: the RealitySync mark. */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true" className={cn("size-8", className)}>
      <rect width="32" height="32" rx="9" className="fill-ink-950" />
      <path
        d="M10 13.5a6.5 6.5 0 0 1 11.6-3.9M22 18.5a6.5 6.5 0 0 1-11.6 3.9"
        fill="none"
        strokeWidth="2.4"
        strokeLinecap="round"
        className="stroke-on-dark"
      />
      <circle cx="22.4" cy="9" r="2.2" className="fill-moss-500" />
      <circle cx="9.6" cy="23" r="2.2" className="fill-on-dark" />
    </svg>
  );
}
