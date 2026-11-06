import { useEffect, useRef, useState } from "react";

/** Polls an async loader on an interval. Returns { data, loading, error, refresh }.
 *
 * The loader is only re-run when `deps` change or `refresh()` is called.
 */
export function usePoll<T>(
  loader: () => Promise<T>,
  { intervalMs = 3000, deps = [] as unknown[], enabled = true }: { intervalMs?: number; deps?: unknown[]; enabled?: boolean } = {}
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const mounted = useRef(true);

  const run = async () => {
    try {
      const d = await loader();
      if (mounted.current) {
        setData(d);
        setError(null);
      }
    } catch (e) {
      if (mounted.current) setError(e instanceof Error ? e.message : String(e));
    } finally {
      if (mounted.current) setLoading(false);
    }
  };

  useEffect(() => {
    mounted.current = true;
    if (enabled) {
      run();
      timer.current = setInterval(run, intervalMs);
    }
    return () => {
      mounted.current = false;
      if (timer.current) clearInterval(timer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, intervalMs, ...deps]);

  return { data, loading, error, refresh: run };
}
