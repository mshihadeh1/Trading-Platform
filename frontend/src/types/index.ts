// Candlestick chart data
export interface CandleData {
  timestamp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

// AI trading signal
export interface Signal {
  id: number;
  symbol: string;
  exchange?: string;
  direction: 'buy' | 'sell' | 'hold';
  entry_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
  take_profit_2: number | null;
  confidence: number;
  reasoning: string;
  timestamp: string | null;
}

// Symbol / watchlist item
export interface SymbolInfo {
  symbol_id: number;
  symbol: string;
  display_name: string;
  exchange: string;
  asset_type: string;
  is_active: boolean;
  added_at: string;
}

// Trade
export interface Trade {
  id: number;
  symbol: string;
  exchange: string;
  side: string;
  entry_price: number;
  quantity: number;
  stop_loss: number | null;
  take_profit: number | null;
  exit_price: number | null;
  pnl: number | null;
  pnl_percent: number | null;
  status: string;
  trading_mode: string;
  created_at: string;
  closed_at: string | null;
}

// Portfolio summary
export interface PortfolioSummary {
  total_pnl: number;
  total_pnl_pct: number;
  realized_pnl: number;
  unrealized_pnl: number;
  open_positions: number;
  total_trades: number;
  win_rate: number;
  current_equity: number;
}

// Candles API response
export interface CandlesResponse {
  candles: CandleData[];
  symbol: string;
  timeframe: string;
}

// Asset
export interface Asset {
  id: number;
  symbol: string;
  name: string;
  exchange: string;
  asset_type: string;
  active: boolean;
}

// Strategy
export interface Strategy {
  id: number;
  name: string;
  description: string;
  conditions: Record<string, any>[];
  created_at: string | null;
}

// Backtest result
export interface BacktestResult {
  total_trades: number;
  win_rate: number;
  total_return: number;
  total_return_pct: number;
  max_drawdown: number;
  sharpe_ratio: number;
  profit_factor: number;
  equity_curve: { timestamp: string; equity: number }[];
  trade_log: {
    entry_time: string;
    exit_time: string;
    entry: number;
    exit: number;
    side: string;
    pnl: number;
    reason: string;
  }[];
  error?: string;
}
