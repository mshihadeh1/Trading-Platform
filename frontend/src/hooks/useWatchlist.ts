import { useState, useEffect, useCallback } from 'react';
import { watchlist } from '../lib/api';
import type { SymbolInfo } from '../types';

export function useWatchlist() {
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [newSymbol, setNewSymbol] = useState('');

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const data = await watchlist.list();
      setSymbols(data);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const addSymbol = async () => {
    const trimmed = newSymbol.trim().toUpperCase();
    if (!trimmed) return;
    try {
      const isYahooSymbol = trimmed.endsWith('-USD') || /^[A-Z.]+$/.test(trimmed);
      const exchange = isYahooSymbol ? 'yahoo' : 'hyperliquid';
      const symbolName = exchange === 'yahoo' ? trimmed : trimmed.replace('-USD', '');
      const symbolType = trimmed.endsWith('-USD') ? 'crypto' : exchange === 'yahoo' ? 'stock' : 'perp';
      const displayName = exchange === 'hyperliquid' ? `${symbolName}-PERP` : symbolName;
      await watchlist.add(symbolName, exchange, symbolType, displayName);
      setNewSymbol('');
      await load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const removeSymbol = async (id: number) => {
    try {
      await watchlist.remove(id);
      await load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  return { symbols, loading, error, newSymbol, setNewSymbol, addSymbol, removeSymbol, reload: load };
}
