import { useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { useNavigate } from "react-router-dom";

import { signOut } from "../../lib/api/auth";

/** Sign out everywhere this browser knows about: server session, cached data, then the login page. */
export function useSignOut(): () => Promise<void> {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  return useCallback(async () => {
    await signOut();
    // Another user may sign in next on this browser; none of this user's data may linger.
    queryClient.clear();
    navigate("/login", { replace: true });
  }, [queryClient, navigate]);
}
