import { useEffect, useState } from "react";

/** Seconds remaining until `expiresAt` (ISO string), ticking every second. */
export function useCountdown(expiresAt: string | null) {
  const [remaining, setRemaining] = useState(0);

  useEffect(() => {
    if (!expiresAt) {
      setRemaining(0);
      return;
    }
    const target = new Date(expiresAt).getTime();
    const tick = () =>
      setRemaining(Math.max(0, Math.round((target - Date.now()) / 1000)));
    tick();
    const id = window.setInterval(tick, 1000);
    return () => window.clearInterval(id);
  }, [expiresAt]);

  return remaining;
}
