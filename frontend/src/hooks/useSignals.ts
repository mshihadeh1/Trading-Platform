import { useState, useEffect, useCallback } from 'react';
import { signals } from '../lib/api';
import type { Signal } from '../types';

export function useSignals() {
  const [signalsData, setSignalsData] = useState<Signal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await signals.list(30);
      setSignalsData(data);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 120000); // Refresh every 2 min
    return () => clearInterval(interval);
  }, [load]);

  return { signals: signalsData, loading, error, refetch: load };
}
