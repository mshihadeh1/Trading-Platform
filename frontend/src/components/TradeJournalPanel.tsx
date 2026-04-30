import type { Trade } from '../types';

interface Props {
  trades: Trade[];
  loading: boolean;
  error: string | null;
}

function money(value?: number | null) {
  const safe = value ?? 0;
  return `${safe >= 0 ? '+' : '-'}$${Math.abs(safe).toFixed(2)}`;
}

function percent(value?: number | null) {
  const safe = value ?? 0;
  return `${safe >= 0 ? '+' : ''}${safe.toFixed(2)}%`;
}

function tradePnlPct(trade: Trade) {
  return trade.pnl_pct ?? trade.pnl_percent ?? null;
}

export function TradeJournalPanel({ trades, loading, error }: Props) {
  if (error) return <div className="bg-dark-800 rounded-lg border border-dark-600 p-4 text-red-400">Journal unavailable: {error}</div>;
  if (loading) return <div className="bg-dark-800 rounded-lg border border-dark-600 p-4 text-gray-500">Loading trade journal...</div>;

  const journalTrades = trades.slice(0, 12);
  const openTrades = trades.filter(trade => trade.status === 'open');
  const closedTrades = trades.filter(trade => trade.status !== 'open');
  const wins = closedTrades.filter(trade => (trade.pnl ?? 0) > 0);
  const losses = closedTrades.filter(trade => (trade.pnl ?? 0) < 0);
  const realizedPnl = closedTrades.reduce((sum, trade) => sum + (trade.pnl ?? 0), 0);
  const unrealizedPnl = openTrades.reduce((sum, trade) => sum + (trade.pnl ?? 0), 0);
  const avgWin = wins.length ? wins.reduce((sum, trade) => sum + (trade.pnl ?? 0), 0) / wins.length : 0;
  const avgLoss = losses.length ? losses.reduce((sum, trade) => sum + (trade.pnl ?? 0), 0) / losses.length : 0;
  const winRate = closedTrades.length ? (wins.length / closedTrades.length) * 100 : 0;

  return (
    <div className="bg-dark-800 rounded-lg border border-dark-600 overflow-hidden">
      <div className="px-4 py-3 border-b border-dark-600 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300">Trade Journal</h2>
        <span className="text-xs text-gray-500">{openTrades.length} open • {closedTrades.length} closed</span>
      </div>

      <div className="p-4 border-b border-dark-700 grid grid-cols-2 md:grid-cols-5 gap-3 text-xs">
        <div className="rounded border border-dark-700 p-3">
          <div className="text-gray-500 mb-1">Win rate</div>
          <div className="text-white font-semibold">{winRate.toFixed(1)}%</div>
        </div>
        <div className="rounded border border-dark-700 p-3">
          <div className="text-gray-500 mb-1">Realized P&L</div>
          <div className={realizedPnl >= 0 ? 'text-green-400 font-semibold' : 'text-red-400 font-semibold'}>{money(realizedPnl)}</div>
        </div>
        <div className="rounded border border-dark-700 p-3">
          <div className="text-gray-500 mb-1">Unrealized P&L</div>
          <div className={unrealizedPnl >= 0 ? 'text-green-400 font-semibold' : 'text-red-400 font-semibold'}>{money(unrealizedPnl)}</div>
        </div>
        <div className="rounded border border-dark-700 p-3">
          <div className="text-gray-500 mb-1">Avg win</div>
          <div className="text-green-400 font-semibold">{money(avgWin)}</div>
        </div>
        <div className="rounded border border-dark-700 p-3">
          <div className="text-gray-500 mb-1">Avg loss</div>
          <div className="text-red-400 font-semibold">{money(avgLoss)}</div>
        </div>
      </div>

      {journalTrades.length === 0 ? (
        <div className="p-4 text-sm text-gray-500">No trade journal entries yet.</div>
      ) : (
        <div className="divide-y divide-dark-700">
          {journalTrades.map((trade) => {
            const pnl = trade.pnl ?? 0;
            const pnlPct = tradePnlPct(trade);
            const notional = trade.entry_price * trade.quantity;
            return (
              <div key={trade.id} className="p-4 text-sm">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <div className="font-medium text-white">
                      {trade.symbol} {(trade.direction ?? trade.side ?? '').toUpperCase()}
                    </div>
                    <div className="text-xs text-gray-500">
                      Entry ${trade.entry_price.toFixed(4)} • Qty {trade.quantity} • Notional ${notional.toFixed(2)}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className={pnl > 0 ? 'text-green-400' : pnl < 0 ? 'text-red-400' : 'text-gray-400'}>
                      {money(pnl)} {pnlPct !== null ? `(${percent(pnlPct)})` : ''}
                    </div>
                    <div className={`text-xs ${trade.status === 'open' ? 'text-blue-300' : trade.status === 'tp_hit' ? 'text-green-300' : trade.status === 'sl_hit' ? 'text-red-300' : 'text-gray-400'}`}>
                      {trade.status.toUpperCase()}
                    </div>
                  </div>
                </div>
                <div className="mt-2 grid grid-cols-1 md:grid-cols-3 gap-2 text-xs text-gray-500">
                  <div>Entry {trade.entry_time ? new Date(trade.entry_time).toLocaleString() : '-'}</div>
                  <div>{trade.exit_time ? `Exit ${new Date(trade.exit_time).toLocaleString()}` : 'Position still open'}</div>
                  <div>
                    SL {trade.stop_loss ? `$${trade.stop_loss.toFixed(4)}` : '-'} • TP {trade.take_profit ? `$${trade.take_profit.toFixed(4)}` : '-'}
                  </div>
                </div>
                <div className="mt-1 text-xs text-gray-400">
                  {trade.source_signal_id ? `Signal #${trade.source_signal_id}` : 'Manual/unknown source'}
                  {trade.close_reason ? ` • ${trade.close_reason}` : ''}
                  {trade.current_price ? ` • Mark $${trade.current_price.toFixed(4)}` : ''}
                </div>
                {trade.notes && <div className="mt-1 text-xs text-gray-500">{trade.notes}</div>}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
