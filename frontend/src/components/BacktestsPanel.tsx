import type { BacktestResult } from '../types';

interface Props {
  results: BacktestResult[];
  loading: boolean;
  error: string | null;
  onRefresh: () => void;
}

function pct(value?: number) {
  return `${(value ?? 0).toFixed(2)}%`;
}

export function BacktestsPanel({ results, loading, error, onRefresh }: Props) {
  if (error) return <div className="text-red-400 p-4">Error loading backtests: {error}</div>;

  const latest = results[0];
  const equity = latest?.equity_curve ?? [];
  const minEquity = Math.min(...equity.map(point => point.equity), latest?.initial_capital ?? 0);
  const maxEquity = Math.max(...equity.map(point => point.equity), latest?.initial_capital ?? 1);
  const range = Math.max(maxEquity - minEquity, 1);

  return (
    <div className="bg-dark-800 rounded-lg border border-dark-600 overflow-hidden">
      <div className="px-4 py-3 border-b border-dark-600 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300">📈 Backtesting</h2>
        <button onClick={onRefresh} className="px-3 py-1 rounded text-xs bg-dark-700 text-gray-300 hover:bg-dark-600">
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="p-4 text-center text-gray-500">Loading backtests...</div>
      ) : !latest ? (
        <div className="p-6 text-center text-gray-500 text-sm">
          No backtest results yet. Create strategies and run backtests from the API to populate this dashboard.
        </div>
      ) : (
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            <Metric label="Return" value={pct(latest.total_return)} tone={(latest.total_return ?? 0) >= 0 ? 'green' : 'red'} />
            <Metric label="Win Rate" value={pct(latest.win_rate)} />
            <Metric label="Max Drawdown" value={pct(latest.max_drawdown)} tone="red" />
            <Metric label="Profit Factor" value={(latest.profit_factor ?? 0).toFixed(2)} />
            <Metric label="Trades" value={`${latest.trades_count ?? latest.total_trades ?? 0}`} />
            <Metric label="Sharpe" value={(latest.sharpe_ratio ?? 0).toFixed(2)} />
            <Metric label="Avg Win" value={(latest.avg_win ?? 0).toFixed(2)} tone="green" />
            <Metric label="Avg Loss" value={(latest.avg_loss ?? 0).toFixed(2)} tone="red" />
          </div>

          <div className="bg-dark-900 rounded border border-dark-700 p-3">
            <div className="text-xs text-gray-400 mb-2">Latest equity curve</div>
            <div className="h-32 flex items-end gap-1">
              {equity.slice(-80).map((point, index) => {
                const height = 10 + ((point.equity - minEquity) / range) * 90;
                return (
                  <div
                    key={`${point.timestamp}-${index}`}
                    title={`${point.timestamp}: ${point.equity.toFixed(2)}`}
                    className="flex-1 bg-blue-500/80 rounded-t"
                    style={{ height: `${height}%` }}
                  />
                );
              })}
            </div>
          </div>

          <div className="bg-dark-900 rounded border border-dark-700 overflow-hidden">
            <div className="px-3 py-2 text-xs text-gray-400 border-b border-dark-700">Recent simulated trades</div>
            <div className="max-h-64 overflow-auto">
              {(latest.trade_log ?? []).slice(-20).reverse().map((trade, index) => (
                <div key={index} className="grid grid-cols-5 gap-2 px-3 py-2 text-xs border-b border-dark-800">
                  <span className="text-gray-300">{trade.side}</span>
                  <span>Entry {trade.entry?.toFixed?.(2) ?? trade.entry}</span>
                  <span>Exit {trade.exit?.toFixed?.(2) ?? trade.exit}</span>
                  <span className={(trade.pnl ?? 0) >= 0 ? 'text-green-400' : 'text-red-400'}>
                    {trade.pnl?.toFixed?.(2) ?? trade.pnl}
                  </span>
                  <span className="text-gray-500">{trade.reason}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: 'green' | 'red' }) {
  const color = tone === 'green' ? 'text-green-400' : tone === 'red' ? 'text-red-400' : 'text-white';
  return (
    <div className="bg-dark-900 rounded border border-dark-700 p-3">
      <div className="text-xs text-gray-500">{label}</div>
      <div className={`text-lg font-bold ${color}`}>{value}</div>
    </div>
  );
}
