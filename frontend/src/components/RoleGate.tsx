import { Lock } from "lucide-react";
import type { ReactNode } from "react";

import { hasRole, useSession, type Role } from "../store/session";
import { Card, EmptyState, PageHeader } from "./ui";

/** Renders children only for `min` role and above; otherwise explains why (06 §5 role gating). */
export function RoleGate({ min, title, children }: { min: Role; title: string; children: ReactNode }) {
  const user = useSession((state) => state.user);
  if (hasRole(user, min)) return <>{children}</>;
  return (
    <>
      <PageHeader title={title} />
      <Card>
        <EmptyState icon={Lock} title="You don't have access to this page" description="Ask an admin for a role that includes it." />
      </Card>
    </>
  );
}
