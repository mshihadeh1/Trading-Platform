import { useState, useEffect, useCallback, useRef } from 'react';
import { candles as candlesApi } from '../lib/api';
import type { CandleData } from '../types';

export function useCandles(symbolId: number | null, limit: number = 200) {
  const [candles, setCandles] = useState<CandleData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    if (!symbolId) return;
    try {
      setLoading(true);
      const data = await candlesApi.list(symbolId, limit);
      // Convert timestamps from string to number (ms)
      const formatted: CandleData[] = data.candles.map((c: any) => ({
        timestamp: new Date(c.timestamp).getTime(),
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
        volume: c.volume,
      }));
      setCandles(formatted);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [symbolId, limit]);

  useEffect(() => {
    load();
    // Poll every 30s
    intervalRef.current = setInterval(load, 30000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [load]);

  return { candles, loading, error, refetch: load };
}
