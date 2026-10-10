import { Construction, Lock } from "lucide-react";
import { useMatches } from "react-router-dom";

import { Card, PageHeader } from "../components/ui";
import { hasRole, useSession } from "../store/session";
import type { RouteHandle } from "../app/routes";

/** Stand-in for pages not built yet; each feature task replaces its route's page. */
export function Component() {
  const handle = useMatches().at(-1)?.handle as RouteHandle | undefined;
  const user = useSession((state) => state.user);
  if (!handle) return null;

  const allowed = !handle.minRole || hasRole(user, handle.minRole);
  const Icon = allowed ? Construction : Lock;

  return (
    <>
      <PageHeader title={handle.title} subtitle={handle.subtitle} />
      <Card className="flex flex-col items-center gap-3 px-6 py-16 text-center">
        <span
          className={
            allowed
              ? "grid size-12 place-items-center rounded-pill bg-neutral-bg text-neutral-fg"
              : "grid size-12 place-items-center rounded-pill bg-rose-bg text-rose-fg"
          }
        >
          <Icon size={20} strokeWidth={1.75} aria-hidden="true" />
        </span>
        <h2 className="text-h3 text-ink-950">
          {allowed ? "This screen is on its way" : "You don't have access to this page"}
        </h2>
        <p className="max-w-sm text-small text-ink-500">
          {allowed
            ? `It is built in ${handle.task} (see docs/09_TASKS.md).`
            : "Ask an admin for a role that includes it."}
        </p>
      </Card>
    </>
  );
}
