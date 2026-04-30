import type { SystemStatus } from '../types';

interface Props {
  status: SystemStatus | null;
  error: string | null;
}

function statusColor(value: boolean) {
  return value ? 'text-green-300 bg-green-900/30' : 'text-yellow-300 bg-yellow-900/30';
}

export function SystemStatusPanel({ status, error }: Props) {
  if (error) {
    return <div className="bg-dark-800 rounded-lg border border-dark-600 p-4 text-red-400">Status unavailable: {error}</div>;
  }

  if (!status) {
    return <div className="bg-dark-800 rounded-lg border border-dark-600 p-4 text-gray-500">Loading system status...</div>;
  }

  const taskEntries = Object.entries(status.tasks).slice(0, 4);

  return (
    <div className="bg-dark-800 rounded-lg border border-dark-600 overflow-hidden">
      <div className="px-4 py-3 border-b border-dark-600">
        <h2 className="text-sm font-semibold text-gray-300">System Status</h2>
      </div>
      <div className="p-4 space-y-4">
        <div className="flex flex-wrap gap-2 text-xs">
          <span className={`px-2 py-1 rounded ${statusColor(status.components.backend)}`}>Backend</span>
          <span className={`px-2 py-1 rounded ${statusColor(status.components.redis)}`}>Redis</span>
          <span className={`px-2 py-1 rounded ${statusColor(status.components.llm_endpoint)}`}>LLM</span>
          <span className={`px-2 py-1 rounded ${status.latest_candle?.fresh ? 'text-green-300 bg-green-900/30' : 'text-red-300 bg-red-900/30'}`}>
            {status.latest_candle?.fresh ? 'Fresh candles' : 'Stale candles'}
          </span>
        </div>

        {status.latest_candle && (
          <div className="text-xs text-gray-400">
            Latest candle: {status.latest_candle.symbol} on {status.latest_candle.exchange} • {Math.floor(status.latest_candle.age_seconds / 60)}m old
          </div>
        )}

        <div className="grid grid-cols-2 gap-3 text-xs">
          <div className="rounded border border-dark-700 p-3">
            <div className="text-gray-500 mb-1">Auto-trade confidence</div>
            <div className="text-white font-semibold">{status.risk_limits.auto_trade_min_confidence}%</div>
          </div>
          <div className="rounded border border-dark-700 p-3">
            <div className="text-gray-500 mb-1">Max open trades</div>
            <div className="text-white font-semibold">{status.risk_limits.max_open_trades}</div>
          </div>
          <div className="rounded border border-dark-700 p-3">
            <div className="text-gray-500 mb-1">Max position size</div>
            <div className="text-white font-semibold">{status.risk_limits.max_position_pct}% equity</div>
          </div>
          <div className="rounded border border-dark-700 p-3">
            <div className="text-gray-500 mb-1">Min risk/reward</div>
            <div className="text-white font-semibold">{status.risk_limits.min_risk_reward_ratio.toFixed(1)}x</div>
          </div>
        </div>

        <div>
          <div className="text-xs font-semibold text-gray-400 mb-2">Recent Tasks</div>
          {taskEntries.length === 0 ? (
            <div className="text-xs text-gray-500">Tasks will appear after the worker completes collection, analysis, or SL/TP checks.</div>
          ) : (
            <div className="space-y-2">
              {taskEntries.map(([key, value]) => (
                <div key={key} className="rounded border border-dark-700 p-2 text-xs">
                  <div className="text-gray-300">{key.replace('task.', '')}</div>
                  <div className="text-gray-500">
                    {value.updated_at ? new Date(value.updated_at).toLocaleString() : 'No timestamp'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
