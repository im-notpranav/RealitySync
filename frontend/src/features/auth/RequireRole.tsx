import { Outlet } from "react-router-dom";

import { RoleGate } from "../../components/RoleGate";
import type { Role } from "../../store/session";

/** Route-level role guard (02 §3.1): the page module is not even loaded for a lower role. */
export function RequireRole({ min, title }: { min: Role; title: string }) {
  return (
    <RoleGate min={min} title={title}>
      <Outlet />
    </RoleGate>
  );
}
