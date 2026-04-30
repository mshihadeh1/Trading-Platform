import type { ComponentStatus, SystemStatus } from '../types';

interface Props {
  status: SystemStatus | null;
  error: string | null;
}

function isOk(value: boolean | ComponentStatus | undefined) {
  if (typeof value === 'boolean') return value;
  return value?.status === 'ok';
}

function statusColor(value: boolean | ComponentStatus | undefined) {
  return isOk(value) ? 'text-green-300 bg-green-900/30' : 'text-yellow-300 bg-yellow-900/30';
}

function freshnessColor(fresh?: boolean) {
  if (fresh) return 'text-green-300 bg-green-900/30 border-green-800/60';
  return 'text-red-300 bg-red-900/20 border-red-800/60';
}

function formatAge(seconds?: number) {
  if (seconds === undefined || seconds === null) return 'unknown age';
  if (seconds < 60) return `${seconds}s old`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m old`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m old`;
}

function formatTime(value?: string | null) {
  return value ? new Date(value).toLocaleString() : 'No timestamp';
}

export function SystemStatusPanel({ status, error }: Props) {
  if (error) {
    return <div className="bg-dark-800 rounded-lg border border-dark-600 p-4 text-red-400">Status unavailable: {error}</div>;
  }

  if (!status) {
    return <div className="bg-dark-800 rounded-lg border border-dark-600 p-4 text-gray-500">Loading system status...</div>;
  }

  const taskEntries = Object.entries(status.tasks).slice(0, 6);
  const latestCandle = status.data ?? (status.latest_candle ? {
    symbol: status.latest_candle.symbol,
    exchange: status.latest_candle.exchange,
    latest_candle_at: status.latest_candle.timestamp,
    age_seconds: status.latest_candle.age_seconds,
    fresh: status.latest_candle.fresh,
  } : undefined);

  const diagnostics = [
    {
      label: 'Market data',
      state: latestCandle?.fresh ? 'Fresh' : 'Stale/missing',
      detail: latestCandle?.latest_candle_at
        ? `${latestCandle.symbol} ${latestCandle.exchange} • ${formatAge(latestCandle.age_seconds)}`
        : 'No candle data recorded yet',
      ok: latestCandle?.fresh,
    },
    {
      label: 'Signals',
      state: status.signals?.fresh ? 'Fresh' : status.signals?.latest_signal_at ? 'Stale' : 'Missing',
      detail: status.signals?.latest_signal_at
        ? `${status.signals.symbol} ${status.signals.direction} ${status.signals.confidence}% • ${formatAge(status.signals.age_seconds)}`
        : 'No AI signal generated yet',
      ok: status.signals?.fresh,
    },
    {
      label: 'Daily brief',
      state: status.daily_brief?.fresh ? 'Ready today' : 'Stale/missing',
      detail: status.daily_brief?.latest_brief_at
        ? `${status.daily_brief.market_regime ?? 'unknown regime'} • ${formatAge(status.daily_brief.age_seconds)}`
        : 'Generate a morning brief before trading',
      ok: status.daily_brief?.fresh,
    },
    {
      label: 'Worker',
      state: status.worker?.status === 'ok' ? 'Heartbeat OK' : 'Needs attention',
      detail: status.worker?.last_heartbeat_at ? `Last heartbeat ${formatTime(status.worker.last_heartbeat_at)}` : 'No worker heartbeat yet',
      ok: status.worker?.status === 'ok',
    },
  ];

  return (
    <div className="bg-dark-800 rounded-lg border border-dark-600 overflow-hidden">
      <div className="px-4 py-3 border-b border-dark-600 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-gray-300">System Status</h2>
        <span className={`px-2 py-1 rounded text-xs ${status.status === 'ok' ? 'text-green-300 bg-green-900/30' : 'text-red-300 bg-red-900/30'}`}>
          {status.status.toUpperCase()}
        </span>
      </div>
      <div className="p-4 space-y-4">
        <div className="flex flex-wrap gap-2 text-xs">
          <span className={`px-2 py-1 rounded ${statusColor(status.components.backend)}`}>Backend</span>
          <span className={`px-2 py-1 rounded ${statusColor(status.components.database)}`}>Database</span>
          <span className={`px-2 py-1 rounded ${statusColor(status.components.redis)}`}>Redis</span>
          <span className={`px-2 py-1 rounded ${statusColor(status.components.llm ?? status.components.llm_endpoint)}`}>LLM</span>
          <span className={`px-2 py-1 rounded ${status.worker?.status === 'ok' ? 'text-green-300 bg-green-900/30' : 'text-yellow-300 bg-yellow-900/30'}`}>Worker</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3 text-xs">
          {diagnostics.map(item => (
            <div key={item.label} className={`rounded border p-3 ${freshnessColor(item.ok)}`}>
              <div className="text-gray-400 mb-1">{item.label}</div>
              <div className="font-semibold text-white">{item.state}</div>
              <div className="mt-1 text-gray-400 leading-relaxed">{item.detail}</div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
          <div className="rounded border border-dark-700 p-3">
            <div className="text-gray-500 mb-1">Auto-trade</div>
            <div className={status.risk_limits.auto_trade_enabled ? 'text-green-300 font-semibold' : 'text-yellow-300 font-semibold'}>
              {status.risk_limits.auto_trade_enabled ? 'Enabled' : 'Disabled'}
            </div>
          </div>
          <div className="rounded border border-dark-700 p-3">
            <div className="text-gray-500 mb-1">Min confidence</div>
            <div className="text-white font-semibold">{status.risk_limits.auto_trade_min_confidence}%</div>
          </div>
          <div className="rounded border border-dark-700 p-3">
            <div className="text-gray-500 mb-1">Max open trades</div>
            <div className="text-white font-semibold">{status.risk_limits.max_open_trades}</div>
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
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {taskEntries.map(([key, value]) => (
                <div key={key} className="rounded border border-dark-700 p-2 text-xs">
                  <div className="flex justify-between gap-2">
                    <span className="text-gray-300">{key.replace('task.', '')}</span>
                    <span className={value.status === 'ok' ? 'text-green-400' : 'text-yellow-400'}>{value.status ?? 'unknown'}</span>
                  </div>
                  <div className="text-gray-500">{formatTime(value.updated_at)}</div>
                  {(value.symbols !== undefined || value.candles_stored !== undefined || value.closed_trades !== undefined) && (
                    <div className="text-gray-500 mt-1">
                      {value.symbols !== undefined ? `${value.symbols} symbols` : ''}
                      {value.candles_stored !== undefined ? ` • ${value.candles_stored} candles` : ''}
                      {value.closed_trades !== undefined ? ` • ${value.closed_trades} closed` : ''}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
