// BASE is '/api' which is proxied by Vite to http://localhost:8000
// API paths should NOT include /api prefix since BASE already provides it
const BASE = '/api';

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${res.statusText}`);
  return res.json();
}

// Watchlist
export const watchlist = {
  list: () => fetchJson<import('../types').SymbolInfo[]>(`${BASE}/watchlist`),
  add: (symbol: string, exchange: string) =>
    fetchJson<import('../types').SymbolInfo>(`${BASE}/watchlist`, {
      method: 'POST',
      body: JSON.stringify({ symbol, exchange, is_active: true }),
    }),
  remove: (id: number) =>
    fetchJson(`${BASE}/watchlist/${id}`, { method: 'DELETE' }),
};

// Candles
export const candles = {
  list: (symbolId: number, limit: number = 200) =>
    fetchJson<import('../types').CandlesResponse>(
      `${BASE}/candles/${symbolId}?limit=${limit}`
    ),
};

// Signals
export const signals = {
  list: (limit: number = 50) =>
    fetchJson<import('../types').Signal[]>(`${BASE}/signals?limit=${limit}`),
  trigger: (symbol: string) =>
    fetchJson<{ task_id: string }>(`${BASE}/signals/analyze/${symbol}`),
};

// Trades / Portfolio
export const portfolio = {
  summary: () => fetchJson<import('../types').PortfolioSummary>(`${BASE}/portfolio/summary`),
  list: () => fetchJson<import('../types').Trade[]>(`${BASE}/trades`),
  execute: (data: { symbol: string; quantity: number; price: number; side: string }) =>
    fetchJson<import('../types').Trade>(`${BASE}/trades/execute`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};
