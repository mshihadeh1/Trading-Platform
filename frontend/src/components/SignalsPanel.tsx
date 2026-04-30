import type { Signal } from '../types';

interface Props {
  signals: Signal[];
  loading: boolean;
  error: string | null;
}

const directionColors: Record<string, string> = {
  buy: 'text-green-400 bg-green-900/30',
  sell: 'text-red-400 bg-red-900/30',
  hold: 'text-yellow-400 bg-yellow-900/30',
};

const directionLabel: Record<string, string> = {
  buy: '🟢 BUY',
  sell: '🔴 SELL',
  hold: '🟡 HOLD',
};

export function SignalsPanel({ signals, loading, error }: Props) {
  if (error) return <div className="text-red-400 p-4">Error loading signals: {error}</div>;

  const riskReward = (signal: Signal) => {
    if (!signal.entry_price || !signal.stop_loss || !signal.take_profit) return null;
    if (signal.direction === 'buy') {
      const risk = signal.entry_price - signal.stop_loss;
      const reward = signal.take_profit - signal.entry_price;
      return risk > 0 ? reward / risk : null;
    }
    if (signal.direction === 'sell') {
      const risk = signal.stop_loss - signal.entry_price;
      const reward = signal.entry_price - signal.take_profit;
      return risk > 0 ? reward / risk : null;
    }
    return null;
  };

  return (
    <div className="bg-dark-800 rounded-lg border border-dark-600 overflow-hidden">
      <div className="px-4 py-3 border-b border-dark-600">
        <h2 className="text-sm font-semibold text-gray-300">🤖 AI Signals</h2>
      </div>
      {loading ? (
        <div className="p-4 text-center text-gray-500">Loading signals...</div>
      ) : signals.length === 0 ? (
        <div className="p-4 text-center text-gray-500 text-sm">No signals yet. Analysis runs every 4 hours.</div>
      ) : (
        <div className="max-h-96 overflow-y-auto">
          {signals.map(signal => (
            <div key={signal.id} className="px-4 py-3 border-b border-dark-700 hover:bg-dark-700/50">
              <div className="flex items-center justify-between mb-1">
                <span className="font-bold text-sm">{signal.display_name ?? signal.symbol}</span>
                <span className={`px-2 py-0.5 rounded text-xs font-bold ${directionColors[signal.direction] || ''}`}>
                  {directionLabel[signal.direction] || signal.direction}
                </span>
              </div>
              <div className="text-xs text-gray-400 flex gap-3 mb-1">
                {signal.entry_price && <span>Entry: ${signal.entry_price.toFixed(2)}</span>}
                {signal.stop_loss && <span>SL: ${signal.stop_loss.toFixed(2)}</span>}
                {signal.take_profit && <span>TP: ${signal.take_profit.toFixed(2)}</span>}
                <span>Confidence: {signal.confidence}%</span>
                {riskReward(signal) !== null && <span>R:R {riskReward(signal)?.toFixed(2)}x</span>}
              </div>
              {signal.confidence < 65 && (
                <div className="text-xs text-yellow-400 mb-1">Below auto-trade confidence threshold</div>
              )}
              {signal.paper_trade_id && (
                <div className="text-xs text-blue-300 mb-1">Paper trade #{signal.paper_trade_id} opened</div>
              )}
              {signal.reasoning && (
                <p className="text-xs text-gray-500 mt-1 line-clamp-2">{signal.reasoning}</p>
              )}
              <div className="text-xs text-gray-600 mt-1">
                {signal.timestamp ? new Date(signal.timestamp).toLocaleString() : 'Pending timestamp'}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
