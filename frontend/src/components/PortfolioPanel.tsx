import type { PortfolioSummary, Trade } from '../types';

interface Props {
  summary: PortfolioSummary | null;
  trades: Trade[];
  loading: boolean;
  error: string | null;
}

export function PortfolioPanel({ summary, trades, loading, error }: Props) {
  if (error) return <div className="text-red-400 p-4">Error: {error}</div>;

  const pnlClass = (v: number | null) => {
    if (v === null) return 'text-gray-400';
    return v > 0 ? 'text-green-400' : v < 0 ? 'text-red-400' : 'text-gray-400';
  };

  return (
    <div className="bg-dark-800 rounded-lg border border-dark-600 overflow-hidden">
      <div className="px-4 py-3 border-b border-dark-600">
        <h2 className="text-sm font-semibold text-gray-300">💼 Portfolio (Paper Trading)</h2>
      </div>

      {loading ? (
        <div className="p-4 text-center text-gray-500">Loading...</div>
      ) : (
        <>
          {summary && (
            <div className="p-4 grid grid-cols-3 gap-4 border-b border-dark-600">
              <div>
                <div className="text-xs text-gray-500">Equity</div>
                <div className="text-lg font-bold">${summary.current_equity.toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Total P&L</div>
                <div className={`text-lg font-bold ${pnlClass(summary.total_pnl)}`}>
                  {summary.total_pnl >= 0 ? '+' : ''}${summary.total_pnl.toFixed(2)}
                  <span className="text-sm ml-1">({summary.total_pnl_pct.toFixed(1)}%)</span>
                </div>
              </div>
              <div>
                <div className="text-xs text-gray-500">Win Rate</div>
                <div className={`text-lg font-bold ${pnlClass(summary.total_pnl)}`}>
                  {summary.win_rate.toFixed(0)}%
                </div>
              </div>
            </div>
          )}

          {/* Open trades */}
          {trades.length > 0 && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-xs text-gray-500 border-b border-dark-600">
                    <th className="px-4 py-2 text-left">Symbol</th>
                    <th className="px-4 py-2 text-left">Side</th>
                    <th className="px-4 py-2 text-right">Entry</th>
                    <th className="px-4 py-2 text-right">SL</th>
                    <th className="px-4 py-2 text-right">TP</th>
                    <th className="px-4 py-2 text-right">P&L</th>
                    <th className="px-4 py-2 text-center">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {trades.slice(0, 20).map(trade => (
                    <tr key={trade.id} className="border-b border-dark-700 hover:bg-dark-700/30">
                      <td className="px-4 py-2 font-medium">{trade.symbol}</td>
                      <td className={`px-4 py-2 text-xs font-bold uppercase ${trade.side === 'buy' ? 'text-green-400' : 'text-red-400'}`}>
                        {trade.side}
                      </td>
                      <td className="px-4 py-2 text-right">${trade.entry_price.toFixed(2)}</td>
                      <td className="px-4 py-2 text-right text-red-400">{trade.stop_loss ? `$${trade.stop_loss.toFixed(2)}` : '-'}</td>
                      <td className="px-4 py-2 text-right text-green-400">{trade.take_profit ? `$${trade.take_profit.toFixed(2)}` : '-'}</td>
                      <td className={`px-4 py-2 text-right font-medium ${pnlClass(trade.pnl)}`}>
                        {trade.pnl !== null ? (trade.pnl >= 0 ? '+' : '') + `$${trade.pnl.toFixed(2)}` : '-'}
                      </td>
                      <td className="px-4 py-2 text-center">
                        <span className={`px-2 py-0.5 rounded text-xs ${
                          trade.status === 'open' ? 'bg-blue-900/50 text-blue-300' :
                          trade.status === 'tp_hit' ? 'bg-green-900/50 text-green-300' :
                          trade.status === 'sl_hit' ? 'bg-red-900/50 text-red-300' :
                          'bg-gray-700 text-gray-300'
                        }`}>
                          {trade.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {trades.length === 0 && (
            <div className="p-6 text-center text-gray-500 text-sm">
              No trades yet. Add symbols and wait for signals!
            </div>
          )}
        </>
      )}
    </div>
  );
}
