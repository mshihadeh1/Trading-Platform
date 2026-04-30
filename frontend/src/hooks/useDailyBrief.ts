import { useCallback, useEffect, useState } from 'react';

import { dailyBrief } from '../lib/api';
import type { DailyBrief } from '../types';

export function useDailyBrief() {
  const [brief, setBrief] = useState<DailyBrief | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await dailyBrief.latest();
      setBrief(data);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  const generate = useCallback(async () => {
    try {
      setGenerating(true);
      const data = await dailyBrief.generate();
      setBrief(data);
      setError(null);
      return data;
    } catch (e: any) {
      setError(e.message);
      throw e;
    } finally {
      setGenerating(false);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 300000);
    return () => clearInterval(interval);
  }, [load]);

  return { brief, loading, generating, error, refetch: load, generate };
}
