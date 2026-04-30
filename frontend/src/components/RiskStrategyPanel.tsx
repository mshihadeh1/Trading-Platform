import { useEffect, useState } from 'react';
import { risk, strategies } from '../lib/api';
import type { PositionSizeResponse, RiskProfile, StrategyTemplate, SymbolInfo } from '../types';

interface Props {
  activeSymbol: SymbolInfo | null;
}

export function RiskStrategyPanel({ activeSymbol }: Props) {
  const [profile, setProfile] = useState<RiskProfile | null>(null);
  const [templates, setTemplates] = useState<StrategyTemplate[]>([]);
  const [positionSize, setPositionSize] = useState<PositionSizeResponse | null>(null);
  const [entry, setEntry] = useState('100');
  const [stop, setStop] = useState('95');
  const [method, setMethod] = useState<'fixed_fractional' | 'volatility_atr' | 'kelly'>('fixed_fractional');
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    Promise.all([risk.profile(), strategies.templates()])
      .then(([riskProfile, strategyTemplates]) => {
        if (!mounted) return;
        setProfile(riskProfile);
        setTemplates(strategyTemplates);
      })
      .catch((err) => setMessage(err instanceof Error ? err.message : 'Failed to load risk tools'))
      .finally(() => mounted && setLoading(false));
    return () => {
      mounted = false;
    };
  }, []);

  const calculate = async () => {
    setMessage(null);
    try {
      const result = await risk.positionSize({
        symbol: activeSymbol?.symbol ?? 'BTC',
        direction: 'long',
        entry_price: Number(entry),
        stop_loss: Number(stop),
        method,
        risk_pct: method === 'fixed_fractional' ? profile?.default_risk_pct ?? 1 : undefined,
        win_rate: method === 'kelly' ? 55 : undefined,
        reward_risk: method === 'kelly' ? 2 : undefined,
        atr: method === 'volatility_atr' ? Math.abs(Number(entry) - Number(stop)) : undefined,
        max_position_pct: profile?.max_position_pct,
      });
      setPositionSize(result);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Position sizing failed');
    }
  };

  const createTemplate = async (templateId: string) => {
    setMessage(null);
    try {
      const created = await strategies.createFromTemplate(templateId);
      setMessage(`Created strategy: ${created.name}`);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Failed to create strategy');
    }
  };

  if (loading) {
    return <div className="bg-dark-800 rounded-lg border border-dark-600 p-4 text-gray-400">Loading risk tools...</div>;
  }

  return (
    <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
      <div className="bg-dark-800 rounded-lg border border-dark-600 p-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-white">Risk Manager</h3>
            <p className="text-xs text-gray-500">Fixed-fractional, volatility ATR, and Kelly position sizing</p>
          </div>
          {profile && <span className="text-xs text-gray-400">Max position {profile.max_position_pct}%</span>}
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
          <label className="text-xs text-gray-400">
            Entry
            <input value={entry} onChange={(e) => setEntry(e.target.value)} className="mt-1 w-full bg-dark-700 border border-dark-600 rounded px-2 py-1 text-white" />
          </label>
          <label className="text-xs text-gray-400">
            Stop
            <input value={stop} onChange={(e) => setStop(e.target.value)} className="mt-1 w-full bg-dark-700 border border-dark-600 rounded px-2 py-1 text-white" />
          </label>
          <label className="text-xs text-gray-400">
            Method
            <select value={method} onChange={(e) => setMethod(e.target.value as typeof method)} className="mt-1 w-full bg-dark-700 border border-dark-600 rounded px-2 py-1 text-white">
              <option value="fixed_fractional">Fixed fractional</option>
              <option value="volatility_atr">Volatility ATR</option>
              <option value="kelly">Quarter Kelly</option>
            </select>
          </label>
          <button onClick={calculate} className="self-end bg-emerald-700 hover:bg-emerald-600 text-white rounded px-3 py-2 text-sm">
            Size Trade
          </button>
        </div>

        {positionSize && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <Metric label="Quantity" value={positionSize.quantity.toLocaleString()} />
            <Metric label="Notional" value={`$${positionSize.notional.toLocaleString()}`} />
            <Metric label="Risk" value={`$${positionSize.risk_amount.toLocaleString()}`} />
            <Metric label="Risk %" value={`${positionSize.actual_risk_pct}%`} />
            {positionSize.warnings.map((warning) => (
              <div key={warning} className="col-span-full text-xs text-yellow-400">{warning}</div>
            ))}
          </div>
        )}
        {message && <div className="mt-3 text-xs text-blue-300">{message}</div>}
      </div>

      <div className="bg-dark-800 rounded-lg border border-dark-600 p-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-lg font-semibold text-white">Strategy Templates</h3>
            <p className="text-xs text-gray-500">Pre-built RSI, MACD, Bollinger, EMA, and volume setups</p>
          </div>
          <span className="text-xs text-gray-400">{templates.length} templates</span>
        </div>
        <div className="space-y-3 max-h-80 overflow-auto">
          {templates.map((template) => (
            <div key={template.id} className="border border-dark-600 rounded p-3 bg-dark-700/50">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <div className="text-sm font-semibold text-white">{template.name}</div>
                  <div className="text-xs text-gray-400">{template.description}</div>
                </div>
                <button onClick={() => createTemplate(template.id)} className="shrink-0 bg-blue-700 hover:bg-blue-600 text-white rounded px-3 py-1 text-xs">
                  Add
                </button>
              </div>
              <div className="mt-2 flex flex-wrap gap-2 text-xs">
                <span className="text-purple-300">{template.category}</span>
                <span className="text-gray-400">{template.timeframe}</span>
                <span className="text-emerald-300">Risk {template.risk_profile.default_risk_pct}%</span>
                <span className="text-yellow-300">R:R {template.risk_profile.target_reward_risk}</span>
              </div>
            </div>
          ))}
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
