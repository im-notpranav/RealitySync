import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useSession } from "../../store/session";
import { loginPath } from "./redirect";
import { SessionSplash } from "./SessionSplash";
import { useSessionBootstrap } from "./useSessionBootstrap";

/** Every signed-in route sits under this guard: restore the session, else send the user to sign in. */
export function RequireAuth() {
  const status = useSession((state) => state.status);
  const { pathname, search } = useLocation();
  useSessionBootstrap();

  if (status === "unknown") return <SessionSplash />;
  if (status === "anonymous") return <Navigate to={loginPath(pathname + search)} replace />;
  return <Outlet />;
}
