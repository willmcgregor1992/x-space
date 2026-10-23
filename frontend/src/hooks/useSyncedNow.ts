import { useEffect, useState } from "react";

export function useSyncedNow(serverTime: string | undefined, intervalMs = 250): Date {
  const [now, setNow] = useState(() => (serverTime ? new Date(serverTime) : new Date()));

  useEffect(() => {
    const origin = serverTime ? new Date(serverTime).getTime() : Date.now();
    const captured = performance.now();
    const tick = () => {
      setNow(new Date(origin + (performance.now() - captured)));
    };
    tick();
    const id = window.setInterval(tick, intervalMs);
    return () => window.clearInterval(id);
  }, [serverTime, intervalMs]);

  return now;
}
