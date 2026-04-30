const BASE = '/api';

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${res.statusText}`);
  return res.json();
}

// Watchlist
export const watchlist = {
  list: () => fetchJson<import('../types').SymbolInfo[]>('/watchlist'),
  add: (symbol: string, exchange: string, symbolType: string, displayName: string) =>
    fetchJson<import('../types').SymbolInfo>('/watchlist', {
      method: 'POST',
      body: JSON.stringify({ symbol, exchange, symbol_type: symbolType, display_name: displayName }),
    }),
  remove: (id: number) => fetchJson(`/watchlist/${id}`, { method: 'DELETE' }),
};

// Candles
export const candles = {
  list: (symbolId: number, limit: number = 200) =>
    fetchJson<import('../types').CandlesResponse>(`/candles/${symbolId}?limit=${limit}`),
  refresh: (symbolId: number, timeframe: string = '1h') =>
    fetchJson<{ candles_stored: number; symbol: string }>(`/candles/fetch/${symbolId}?timeframe=${timeframe}`, {
      method: 'POST',
    }),
};

// Signals
export const signals = {
  list: (limit: number = 50) => fetchJson<import('../types').Signal[]>(`/signals?limit=${limit}`),
  trigger: (symbol: string) =>
    fetchJson<{ task_id: string }>(`/signals/analyze/${symbol}`, { method: 'POST' }),
};

// Trades / Portfolio
export const portfolio = {
  summary: () => fetchJson<import('../types').PortfolioSummary>('/portfolio/summary'),
  list: () => fetchJson<import('../types').Trade[]>('/portfolio'),
  execute: (data: { symbol: string; quantity: number; price: number; side: string }) =>
    fetchJson<import('../types').Trade>('/trades/execute', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

export const dailyBrief = {
  latest: () => fetchJson<import('../types').DailyBrief | null>('/daily-brief/latest'),
  history: (limit: number = 20) => fetchJson<import('../types').DailyBrief[]>(`/daily-brief/history?limit=${limit}`),
  generate: () => fetchJson<import('../types').DailyBrief>('/daily-brief/generate', { method: 'POST' }),
};

export const system = {
  status: () => fetchJson<import('../types').SystemStatus>('/health/status'),
};
