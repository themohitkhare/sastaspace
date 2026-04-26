'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

const ADMIN_API_URL = process.env.NEXT_PUBLIC_ADMIN_API_URL ?? 'https://api.sastaspace.com';

export function usePoll<T>(path: string, intervalMs: number): { data: T | null; loading: boolean; error: string | null } {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const skip = path.startsWith('__skip__');

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
    if (skip) {
      setLoading(false);
      return;
    }
    void fetch_();
    const id = setInterval(() => void fetch_(), intervalMs);
    return () => {
      clearInterval(id);
      abortRef.current?.abort();
    };
  }, [fetch_, intervalMs, skip]);

  return { data, loading, error };
}
