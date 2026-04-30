import { useEffect, useState } from 'react';
import { backtests as backtestsApi } from '../lib/api';
import type { BacktestResult } from '../types';

export function useBacktests() {
  const [results, setResults] = useState<BacktestResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refetch = async () => {
    try {
      setLoading(true);
      setError(null);
      setResults(await backtestsApi.list());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load backtests');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refetch();
  }, []);

  return { results, loading, error, refetch };
}
