import { useState, useEffect, useCallback } from 'react';
import { portfolio } from '../lib/api';
import type { PortfolioSummary, Trade } from '../types';

export function usePortfolio() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [trades, setTrades] = useState<Trade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const [summaryData, tradesData] = await Promise.all([
        portfolio.summary(),
        portfolio.list(),
      ]);
      setSummary(summaryData);
      setTrades(tradesData);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, [load]);

  return { summary, trades, loading, error, refetch: load };
}
