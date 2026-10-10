import type { HTMLAttributes } from "react";

import { cn } from "../../lib/cn";

/** Paper card (06 §6): data always sits on paper, never directly on glass. */
export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-card bg-paper p-5 shadow-card", className)} {...props} />;
}
