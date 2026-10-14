import { useEffect } from "react";

import { refreshAccessToken } from "../../lib/api/auth";
import { useSession } from "../../store/session";

/** On first load, restore the session from the refresh cookie (02 §3.1 silent refresh). */
export function useSessionBootstrap(): void {
  const status = useSession((state) => state.status);
  useEffect(() => {
    // refreshAccessToken is single-flight, so StrictMode's double effect sends one request.
    if (status === "unknown") void refreshAccessToken();
  }, [status]);
}
