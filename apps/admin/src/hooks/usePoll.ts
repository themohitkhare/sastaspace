'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

// Phase 3: default-empty after N6. usePoll skips its fetch when empty so the
// hook stays dormant in builds where the legacy admin-api URL isn't set
// (e.g. post-cutover prod with USE_STDB_ADMIN=true).
const ADMIN_API_URL = process.env.NEXT_PUBLIC_ADMIN_API_URL ?? '';

export function usePoll<T>(path: string, intervalMs: number): { data: T | null; loading: boolean; error: string | null } {
  // Skip when the caller explicitly opts out OR when the legacy admin-api URL
  // is unset (post-N6 default). Either way the hook stays dormant.
  const skip = path.startsWith('__skip__') || !ADMIN_API_URL;
  const [data, setData] = useState<T | null>(null);
  // When skipping, the hook is dormant — start with loading=false so the
  // panels' "loading…" placeholders don't briefly flash before the STDB
  // subscription paints.
  const [loading, setLoading] = useState(!skip);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const fetch_ = useCallback(async () => {
    abortRef.current?.abort();
    const ac = new AbortController();
    abortRef.current = ac;
    try {
      const res = await fetch(`${ADMIN_API_URL}${path}`, { signal: ac.signal });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json() as T;
      setData(json);
      setError(null);
    } catch (e) {
      if ((e as Error).name !== 'AbortError') setError(String(e));
    } finally {
      setLoading(false);
    }
  }, [path]);

  useEffect(() => {
    if (skip) return;
    // Initial fetch on mount and on dep change is the whole point of this
    // hook — the setState inside `fetch_` is intentional, not a render loop.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void fetch_();
    const id = setInterval(() => void fetch_(), intervalMs);
    return () => {
      clearInterval(id);
      abortRef.current?.abort();
    };
  }, [fetch_, intervalMs, skip]);

  return { data, loading, error };
}
