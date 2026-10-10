import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";

import type { Alert } from "../../lib/api/types";
import { liveQueue } from "../../lib/demo/data";
import { env } from "../../lib/env";

/**
 * Demo stand-in for the WebSocket feed (T-032): every 14 s one queued alert arrives in the alerts cache,
 * so the live-row enter + flash (06 §8) can be seen. Returns the ids that just arrived.
 */
export function useDemoLiveAlerts(): ReadonlySet<string> {
  const client = useQueryClient();
  const [newIds, setNewIds] = useState<ReadonlySet<string>>(new Set());
  const index = useRef(0);

  useEffect(() => {
    if (!env.demoData) return;
    const timer = window.setInterval(() => {
      const next = liveQueue[index.current % liveQueue.length];
      if (!next) return;
      index.current += 1;
      const alert: Alert = { ...next, id: `live-${Date.now()}`, created_at: new Date().toISOString() };
      client.setQueryData<Alert[]>(["alerts"], (current) => (current ? [alert, ...current] : current));
      setNewIds(new Set([alert.id]));
    }, 14_000);
    return () => window.clearInterval(timer);
  }, [client]);

  return newIds;
}
