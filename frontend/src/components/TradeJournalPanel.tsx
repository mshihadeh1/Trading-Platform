import type { Trade } from '../types';

interface Props {
  trades: Trade[];
  loading: boolean;
  error: string | null;
}

export function TradeJournalPanel({ trades, loading, error }: Props) {
  if (error) return <div className="bg-dark-800 rounded-lg border border-dark-600 p-4 text-red-400">Journal unavailable: {error}</div>;
  if (loading) return <div className="bg-dark-800 rounded-lg border border-dark-600 p-4 text-gray-500">Loading trade journal...</div>;

  const journalTrades = trades.slice(0, 12);

  return (
    <div className="bg-dark-800 rounded-lg border border-dark-600 overflow-hidden">
      <div className="px-4 py-3 border-b border-dark-600">
        <h2 className="text-sm font-semibold text-gray-300">Trade Journal</h2>
      </div>
      {journalTrades.length === 0 ? (
        <div className="p-4 text-sm text-gray-500">No trade journal entries yet.</div>
      ) : (
        <div className="divide-y divide-dark-700">
          {journalTrades.map((trade) => (
            <div key={trade.id} className="p-4 text-sm">
              <div className="flex items-center justify-between">
                <div className="font-medium text-white">
                  {trade.symbol} {trade.direction ?? trade.side}
                </div>
                <div className={trade.pnl && trade.pnl > 0 ? 'text-green-400' : trade.pnl && trade.pnl < 0 ? 'text-red-400' : 'text-gray-400'}>
                  {trade.pnl !== null ? `${trade.pnl >= 0 ? '+' : ''}$${trade.pnl.toFixed(2)}` : 'Open'}
                </div>
              </div>
              <div className="mt-1 text-xs text-gray-500">
                Entry {trade.entry_time ? new Date(trade.entry_time).toLocaleString() : '-'}
                {trade.exit_time ? ` • Exit ${new Date(trade.exit_time).toLocaleString()}` : ' • Position still open'}
              </div>
              <div className="mt-1 text-xs text-gray-400">
                {trade.source_signal_id ? `Signal #${trade.source_signal_id}` : 'Manual/unknown source'}
                {trade.close_reason ? ` • ${trade.close_reason}` : ''}
              </div>
              {trade.notes && <div className="mt-1 text-xs text-gray-500">{trade.notes}</div>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
