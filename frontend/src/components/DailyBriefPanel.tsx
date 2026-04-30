import type { DailyBrief } from '../types';

interface Props {
  brief: DailyBrief | null;
  loading: boolean;
  generating: boolean;
  error: string | null;
  onGenerate: () => Promise<unknown>;
}

const regimeColors: Record<string, string> = {
  bullish: 'text-green-300 bg-green-900/30',
  'risk-on': 'text-green-300 bg-green-900/30',
  bearish: 'text-red-300 bg-red-900/30',
  'risk-off': 'text-red-300 bg-red-900/30',
  choppy: 'text-yellow-300 bg-yellow-900/30',
  mixed: 'text-blue-300 bg-blue-900/30',
};

function money(value?: number | null) {
  if (value === undefined || value === null) return '—';
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
}

export function DailyBriefPanel({ brief, loading, generating, error, onGenerate }: Props) {
  if (loading) {
    return <div className="bg-dark-800 rounded-lg border border-dark-600 p-4 text-gray-500">Loading daily brief...</div>;
  }

  return (
    <div className="bg-dark-800 rounded-lg border border-dark-600 overflow-hidden">
      <div className="px-4 py-3 border-b border-dark-600 flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-gray-300">🌅 Daily Trading Brief</h2>
          <p className="text-xs text-gray-500">Morning scan, focus list, and paper-risk snapshot</p>
        </div>
        <button
          onClick={onGenerate}
          disabled={generating}
          className="px-3 py-1.5 rounded text-xs font-medium bg-blue-600 text-white hover:bg-blue-500 disabled:opacity-50"
        >
          {generating ? 'Generating...' : brief ? 'Regenerate' : 'Generate Brief'}
        </button>
      </div>

      <div className="p-4 space-y-4">
        {error && <div className="text-sm text-red-400">Daily brief unavailable: {error}</div>}

        {!brief ? (
          <div className="text-sm text-gray-500">
            No daily brief yet. Generate one after candles/signals are available to create a focused trading plan.
          </div>
        ) : (
          <>
            <div className="flex flex-wrap items-center gap-2">
              <span className={`px-2 py-1 rounded text-xs font-bold ${regimeColors[brief.market_regime] ?? regimeColors.mixed}`}>
                {brief.market_regime.toUpperCase()}
              </span>
              <span className="text-xs text-gray-500">
                {new Date(brief.created_at).toLocaleString()} • {brief.brief_date}
              </span>
            </div>

            <p className="text-sm text-gray-300 leading-relaxed">{brief.summary}</p>

            <div className="grid grid-cols-3 gap-3 text-xs">
              <div className="rounded border border-dark-700 p-3">
                <div className="text-gray-500 mb-1">Open positions</div>
                <div className="text-white font-semibold">{brief.open_positions_summary.open_positions ?? 0}</div>
              </div>
              <div className="rounded border border-dark-700 p-3">
                <div className="text-gray-500 mb-1">Exposure</div>
                <div className="text-white font-semibold">{money(brief.open_positions_summary.notional_exposure)}</div>
              </div>
              <div className="rounded border border-dark-700 p-3">
                <div className="text-gray-500 mb-1">Unrealized P&L</div>
                <div className="text-white font-semibold">{money(brief.open_positions_summary.unrealized_pnl)}</div>
              </div>
            </div>

            <div>
              <div className="text-xs font-semibold text-gray-400 mb-2">Top Opportunities</div>
              {brief.top_opportunities.length === 0 ? (
                <div className="text-xs text-gray-500">No high-confidence actionable setups in the latest scan.</div>
              ) : (
                <div className="grid gap-2 lg:grid-cols-3">
                  {brief.top_opportunities.slice(0, 3).map(opportunity => (
                    <div key={`${opportunity.symbol}-${opportunity.signal_id ?? opportunity.timestamp}`} className="rounded border border-dark-700 p-3">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-bold text-white">{opportunity.display_name ?? opportunity.symbol}</span>
                        <span className={opportunity.direction === 'buy' ? 'text-green-400 text-xs font-bold' : 'text-red-400 text-xs font-bold'}>
                          {opportunity.direction.toUpperCase()} {opportunity.confidence}%
                        </span>
                      </div>
                      <div className="text-xs text-gray-400 space-y-1">
                        <div>{opportunity.setup_type ?? 'setup'} • {opportunity.time_horizon ?? 'timeframe'}</div>
                        <div>Entry: {money(opportunity.entry_price ?? opportunity.entry_min)}</div>
                        <div>SL: {money(opportunity.stop_loss)} • TP: {money(opportunity.take_profit)}</div>
                        {opportunity.risk_reward && <div>R:R {opportunity.risk_reward.toFixed(2)}x</div>}
                      </div>
                      {opportunity.reasoning && <p className="text-xs text-gray-500 mt-2 line-clamp-2">{opportunity.reasoning}</p>}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="rounded border border-yellow-900/40 bg-yellow-900/10 p-3 text-xs text-yellow-200">
              {brief.risk_notes}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
