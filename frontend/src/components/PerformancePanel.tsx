import { useEffect, useState } from 'react';
import { portfolio } from '../lib/api';
import type { PortfolioPerformance } from '../types';

export function PerformancePanel() {
  const [performance, setPerformance] = useState<PortfolioPerformance | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    portfolio.performance()
      .then((data) => mounted && setPerformance(data))
      .catch((err) => mounted && setError(err instanceof Error ? err.message : 'Failed to load performance'))
      .finally(() => mounted && setLoading(false));
    return () => {
      mounted = false;
    };
  }, []);

  if (loading) {
    return <div className="bg-dark-800 rounded-lg border border-dark-600 p-4 text-gray-400">Loading performance analytics...</div>;
  }

  if (error || !performance) {
    return <div className="bg-dark-800 rounded-lg border border-dark-600 p-4 text-red-400">{error || 'No performance data'}</div>;
  }

  const monthly = Object.entries(performance.monthly_pnl).slice(-6);
  const maxMonthlyAbs = Math.max(1, ...monthly.map(([, pnl]) => Math.abs(pnl)));
  const curve = performance.equity_curve.slice(-20);
  const minEquity = Math.min(...curve.map((point) => point.equity), performance.initial_capital);
  const maxEquity = Math.max(...curve.map((point) => point.equity), performance.initial_capital);
  const equityRange = Math.max(1, maxEquity - minEquity);

  return (
    <div className="bg-dark-800 rounded-lg border border-dark-600 p-4">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-white">Performance Analytics</h3>
          <p className="text-xs text-gray-500">Equity, drawdown, monthly P&L, and trade quality</p>
        </div>
        <span className={`text-sm font-semibold ${performance.total_return >= 0 ? 'text-green-400' : 'text-red-400'}`}>
          {performance.total_return >= 0 ? '+' : ''}${performance.total_return.toLocaleString()} ({performance.total_return_pct}%)
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 mb-5">
        <Metric label="Equity" value={`$${performance.current_equity.toLocaleString()}`} />
        <Metric label="Win rate" value={`${performance.win_rate}%`} />
        <Metric label="Profit factor" value={performance.profit_factor.toString()} />
        <Metric label="Max DD" value={`${performance.max_drawdown}%`} />
        <Metric label="Trades" value={performance.total_trades.toString()} />
        <Metric label="Avg win" value={`$${performance.avg_win.toLocaleString()}`} />
        <Metric label="Avg loss" value={`$${performance.avg_loss.toLocaleString()}`} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="bg-dark-700 rounded p-3">
          <div className="text-sm font-semibold text-white mb-3">Equity Curve</div>
          {curve.length ? (
            <div className="h-32 flex items-end gap-1">
              {curve.map((point, idx) => {
                const height = 12 + ((point.equity - minEquity) / equityRange) * 108;
                return <div key={`${point.timestamp}-${idx}`} title={`$${point.equity}`} className="flex-1 bg-blue-500 rounded-t" style={{ height }} />;
              })}
            </div>
          ) : (
            <div className="h-32 flex items-center justify-center text-gray-500 text-sm">No closed trades yet</div>
          )}
        </div>

        <div className="bg-dark-700 rounded p-3">
          <div className="text-sm font-semibold text-white mb-3">Monthly P&L</div>
          {monthly.length ? (
            <div className="space-y-2">
              {monthly.map(([month, pnl]) => (
                <div key={month} className="grid grid-cols-[64px_1fr_80px] items-center gap-2 text-xs">
                  <span className="text-gray-400">{month}</span>
                  <div className="h-3 bg-dark-600 rounded overflow-hidden">
                    <div
                      className={`${pnl >= 0 ? 'bg-green-500' : 'bg-red-500'} h-3`}
                      style={{ width: `${Math.max(4, (Math.abs(pnl) / maxMonthlyAbs) * 100)}%` }}
                    />
                  </div>
                  <span className={pnl >= 0 ? 'text-green-400' : 'text-red-400'}>
                    {pnl >= 0 ? '+' : ''}${pnl.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <div className="h-32 flex items-center justify-center text-gray-500 text-sm">No monthly P&L yet</div>
          )}
        </div>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-dark-700 rounded p-3">
      <div className="text-xs text-gray-500">{label}</div>
      <div className="text-base font-semibold text-white">{value}</div>
    </div>
  );
}
