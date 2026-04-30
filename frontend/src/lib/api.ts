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
  execute: (signalId: number, quantity: number = 1) =>
    fetchJson<import('../types').Trade>(`/signals/${signalId}/execute`, {
      method: 'POST',
      body: JSON.stringify({ quantity }),
    }),
};

// Trades / Portfolio
export const portfolio = {
  summary: () => fetchJson<import('../types').PortfolioSummary>('/portfolio/summary'),
  performance: () => fetchJson<import('../types').PortfolioPerformance>('/portfolio/performance'),
  list: () => fetchJson<import('../types').Trade[]>('/portfolio'),
  execute: (data: { symbol: string; quantity: number; price: number; side: string }) =>
    fetchJson<import('../types').Trade>('/trades/execute', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

export const risk = {
  profile: () => fetchJson<import('../types').RiskProfile>('/risk/profile'),
  positionSize: (data: {
    symbol?: string;
    direction: 'long' | 'short';
    entry_price: number;
    stop_loss: number;
    account_equity?: number;
    method: 'fixed_fractional' | 'volatility_atr' | 'kelly';
    risk_pct?: number;
    atr?: number;
    atr_multiple?: number;
    win_rate?: number;
    reward_risk?: number;
    max_position_pct?: number;
  }) => fetchJson<import('../types').PositionSizeResponse>('/risk/position-size', {
    method: 'POST',
    body: JSON.stringify(data),
  }),
};

export const strategies = {
  templates: () => fetchJson<import('../types').StrategyTemplate[]>('/strategies/templates'),
  createFromTemplate: (templateId: string) =>
    fetchJson<import('../types').Strategy>(`/strategies/templates/${templateId}/create`, { method: 'POST' }),
};

export const dailyBrief = {
  latest: () => fetchJson<import('../types').DailyBrief | null>('/daily-brief/latest'),
  history: (limit: number = 20) => fetchJson<import('../types').DailyBrief[]>(`/daily-brief/history?limit=${limit}`),
  generate: () => fetchJson<import('../types').DailyBrief>('/daily-brief/generate', { method: 'POST' }),
};

export const backtests = {
  list: (limit: number = 20) => fetchJson<import('../types').BacktestResult[]>(`/backtest?limit=${limit}`),
  optimize: (data: { base_conditions: Record<string, any>[]; parameter_grid: Record<string, number[]>; mock_metrics?: boolean }) =>
    fetchJson<{ results: Array<Record<string, any>> }>('/backtest/optimize', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
};

export const system = {
  status: () => fetchJson<import('../types').SystemStatus>('/health/status'),
};
