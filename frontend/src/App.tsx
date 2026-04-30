import { useState } from 'react';
import { Sidebar } from './components/Sidebar';
import { Chart } from './components/Chart';
import { SignalsPanel } from './components/SignalsPanel';
import { DailyBriefPanel } from './components/DailyBriefPanel';
import { PortfolioPanel } from './components/PortfolioPanel';
import { SystemStatusPanel } from './components/SystemStatusPanel';
import { TradeJournalPanel } from './components/TradeJournalPanel';
import { BacktestsPanel } from './components/BacktestsPanel';
import { RiskStrategyPanel } from './components/RiskStrategyPanel';
import { PerformancePanel } from './components/PerformancePanel';
import { useWatchlist } from './hooks/useWatchlist';
import { useCandles } from './hooks/useCandles';
import { useSignals } from './hooks/useSignals';
import { usePortfolio } from './hooks/usePortfolio';
import { useSystemStatus } from './hooks/useSystemStatus';
import { useDailyBrief } from './hooks/useDailyBrief';
import { useBacktests } from './hooks/useBacktests';
import { useBrowserNotifications } from './hooks/useBrowserNotifications';
import { useRealtimeStream } from './hooks/useRealtimeStream';
import { candles as candlesApi, signals as signalsApi } from './lib/api';
import type { Signal, SymbolInfo } from './types';

export default function App() {
  const { symbols, loading, error, newSymbol, setNewSymbol, addSymbol, removeSymbol, reload } = useWatchlist();
  const { signals, loading: signalsLoading, error: signalsError, refetch: refetchSignals } = useSignals();
  const { summary, trades, loading: portfolioLoading, error: portfolioError, refetch: refetchPortfolio } = usePortfolio();
  const { status: systemStatus, error: systemError, refetch: refetchSystemStatus } = useSystemStatus();
  const { results: backtests, loading: backtestsLoading, error: backtestsError, refetch: refetchBacktests } = useBacktests();
  const {
    brief: dailyBrief,
    loading: dailyBriefLoading,
    generating: dailyBriefGenerating,
    error: dailyBriefError,
    generate: generateDailyBrief,
  } = useDailyBrief();

  const [activeSymbol, setActiveSymbol] = useState<SymbolInfo | null>(null);
  const [activeTab, setActiveTab] = useState<'chart' | 'portfolio' | 'backtests'>('chart');
  const notifications = useBrowserNotifications({ signals, trades, dailyBrief, systemStatus });
  const realtime = useRealtimeStream();

  const { candles, loading: candlesLoading, error: candlesError, refetch: refetchCandles } = useCandles(
    activeSymbol?.symbol_id ?? null
  );

  const handleSelect = (sym: SymbolInfo) => {
    setActiveSymbol(sym);
  };

  const handleAdd = async () => {
    await addSymbol();
    await reload();
  };

  const handleRefreshActiveSymbol = async () => {
    if (!activeSymbol) return;
    await candlesApi.refresh(activeSymbol.symbol_id);
    await Promise.all([refetchCandles(), refetchSystemStatus()]);
  };

  const handleAnalyzeActiveSymbol = async () => {
    if (!activeSymbol) return;
    await signalsApi.trigger(activeSymbol.symbol);
    await Promise.all([refetchSignals(), refetchPortfolio(), refetchSystemStatus()]);
  };

  const handleExecuteSignal = async (signal: Signal) => {
    await signalsApi.execute(signal.id, 1);
    await Promise.all([refetchSignals(), refetchPortfolio(), refetchSystemStatus()]);
    setActiveTab('portfolio');
  };

  return (
    <div className="flex h-screen bg-dark-900">
      {/* Sidebar */}
      <Sidebar
        symbols={symbols}
        loading={loading}
        newSymbol={newSymbol}
        setNewSymbol={setNewSymbol}
        onAdd={handleAdd}
        onRemove={removeSymbol}
        onSelect={handleSelect}
        activeSymbolId={activeSymbol?.symbol_id ?? null}
      />

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-auto">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-3 border-b border-dark-600 bg-dark-800">
          <div className="flex items-center gap-4">
            {activeSymbol ? (
              <>
                <h2 className="text-xl font-bold text-white">{activeSymbol.display_name}</h2>
                <span className="text-sm text-gray-500">{activeSymbol.symbol}</span>
              </>
            ) : (
              <h2 className="text-xl font-bold text-gray-400">Select a symbol to view chart</h2>
            )}
            {realtime.snapshot?.latest_candle && (
              <span className="text-xs text-gray-400">
                Live {realtime.snapshot.latest_candle.symbol}: ${realtime.snapshot.latest_candle.close.toFixed(2)}
              </span>
            )}
            <span className={`text-xs ${realtime.connected ? 'text-green-400' : 'text-yellow-400'}`}>
              {realtime.connected ? 'WS live' : 'WS reconnecting'}
            </span>
          </div>
          <div className="flex gap-2">
            {activeSymbol && (
              <>
                <button
                  onClick={handleRefreshActiveSymbol}
                  className="px-4 py-2 rounded text-sm font-medium bg-dark-700 text-gray-300 hover:bg-dark-600"
                >
                  Refresh Candles
                </button>
                <button
                  onClick={handleAnalyzeActiveSymbol}
                  className="px-4 py-2 rounded text-sm font-medium bg-emerald-700 text-white hover:bg-emerald-600"
                >
                  Analyze Now
                </button>
              </>
            )}
            <button
              onClick={() => setActiveTab('chart')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                activeTab === 'chart' ? 'bg-blue-600 text-white' : 'bg-dark-700 text-gray-400 hover:bg-dark-600'
              }`}
            >
              Chart
            </button>
            <button
              onClick={() => setActiveTab('portfolio')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                activeTab === 'portfolio' ? 'bg-blue-600 text-white' : 'bg-dark-700 text-gray-400 hover:bg-dark-600'
              }`}
            >
              Portfolio
            </button>
            <button
              onClick={() => setActiveTab('backtests')}
              className={`px-4 py-2 rounded text-sm font-medium transition-colors ${
                activeTab === 'backtests' ? 'bg-blue-600 text-white' : 'bg-dark-700 text-gray-400 hover:bg-dark-600'
              }`}
            >
              Backtests
            </button>
            {notifications.supported && notifications.permission !== 'granted' && (
              <button
                onClick={notifications.requestPermission}
                className="px-4 py-2 rounded text-sm font-medium bg-purple-700 text-white hover:bg-purple-600"
              >
                Enable Alerts
              </button>
            )}
          </div>
        </div>

        {/* Content area */}
        <div className="flex-1 p-4 space-y-4 overflow-auto">
          {activeTab === 'chart' && (
            <>
              {/* Daily Brief */}
              <DailyBriefPanel
                brief={dailyBrief}
                loading={dailyBriefLoading}
                generating={dailyBriefGenerating}
                error={dailyBriefError}
                onGenerate={generateDailyBrief}
              />

              <RiskStrategyPanel activeSymbol={activeSymbol} />

              {/* Chart */}
              <div className="bg-dark-800 rounded-lg border border-dark-600 p-4">
                {activeSymbol ? (
                  candles.length > 0 ? (
                    <Chart candles={candles} symbol={activeSymbol.symbol} height={500} />
                  ) : (
                    <div className="h-[500px] flex items-center justify-center">
                      <div className="text-center">
                        <div className="text-gray-500 mb-2">No candle data available yet</div>
                        <button
                          onClick={refetchCandles}
                          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm"
                        >
                          Refresh
                        </button>
                      </div>
                    </div>
                  )
                ) : (
                  <div className="h-[500px] flex items-center justify-center text-gray-500">
                    Select a symbol from the watchlist
                  </div>
                )}
              </div>

              {/* Signals */}
              <SignalsPanel
                signals={signals}
                loading={signalsLoading}
                error={signalsError}
                onExecute={handleExecuteSignal}
              />
              <SystemStatusPanel status={systemStatus} error={systemError} />
            </>
          )}

          {activeTab === 'portfolio' && (
            <>
              <PerformancePanel />
              <PortfolioPanel
                summary={summary}
                trades={trades}
                loading={portfolioLoading}
                error={portfolioError}
              />
              <TradeJournalPanel trades={trades} loading={portfolioLoading} error={portfolioError} />
            </>
          )}

          {activeTab === 'backtests' && (
            <BacktestsPanel
              results={backtests}
              loading={backtestsLoading}
              error={backtestsError}
              onRefresh={refetchBacktests}
            />
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-2 border-t border-dark-600 text-xs text-gray-600 flex justify-between">
          <span>{symbols.length} symbols • {signals.length} signals</span>
          <div className="flex gap-4">
            <span className={systemStatus?.components.redis && systemStatus?.components.llm_endpoint ? 'text-green-400' : 'text-yellow-400'}>
              {systemError
                ? 'Status unavailable'
                : systemStatus?.latest_candle
                  ? `${systemStatus.latest_candle.symbol} candle age ${Math.floor(systemStatus.latest_candle.age_seconds / 60)}m`
                  : 'Waiting for status'}
            </span>
            <button onClick={reload} className="hover:text-gray-400">Refresh Watchlist</button>
            <button onClick={refetchSignals} className="hover:text-gray-400">Refresh Signals</button>
            <button onClick={refetchPortfolio} className="hover:text-gray-400">Refresh Portfolio</button>
          </div>
        </div>
      </div>
    </div>
  );
}
