import { useCallback, useEffect, useRef, useState } from "react";

export function usePolling(fetcher, intervalMs = 10000, enabled = true) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const fetcherRef = useRef(fetcher);

  fetcherRef.current = fetcher;

  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    setError(null);
    try {
      const result = await fetcherRef.current();
      setData(result);
    } catch (err) {
      setError(err.message || "Failed to load data");
    } finally {
      if (!silent) setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!enabled) return undefined;
    load(false);
    const id = setInterval(() => load(true), intervalMs);
    return () => clearInterval(id);
  }, [enabled, intervalMs, load]);

  return { data, loading, error, refresh: () => load(false) };
}
