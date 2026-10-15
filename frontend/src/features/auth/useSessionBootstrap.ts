import { useEffect } from "react";

import { refreshAccessToken } from "../../lib/api/auth";
import { env } from "../../lib/env";
import { useSession } from "../../store/session";

/** On first load, restore the session from the refresh cookie (02 §3.1 silent refresh). */
export function useSessionBootstrap(): void {
  const status = useSession((state) => state.status);
  useEffect(() => {
    if (status !== "unknown") return;
    // A public demo build has no backend to ask (D-071).
    if (env.demoOnly) useSession.getState().clear();
    // refreshAccessToken is single-flight, so StrictMode's double effect sends one request.
    else void refreshAccessToken();
  }, [status]);
}
