import { cn } from "../../lib/cn";

export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  const letters = parts.length > 1 ? [parts[0], parts[parts.length - 1]] : parts;
  return letters.map((part) => part?.[0]?.toUpperCase() ?? "").join("") || "?";
}

export interface AvatarProps {
  name: string;
  /** `user` = the signed-in person (soft moss); `entity` = a customer (neutral). Entities never have photos. */
  tone?: "user" | "entity";
  size?: "sm" | "md";
  className?: string;
}

export function Avatar({ name, tone = "entity", size = "md", className }: AvatarProps) {
  return (
    <span
      aria-hidden="true"
      className={cn(
        "grid shrink-0 select-none place-items-center rounded-pill font-semibold",
        size === "md" ? "size-10 text-small" : "size-8 text-caption",
        tone === "user"
          ? "bg-gradient-to-br from-moss-bg to-paper text-moss-fg ring-1 ring-white/70"
          : "bg-ink-100 text-ink-700",
        className,
      )}
    >
      {initials(name)}
    </span>
  );
}
