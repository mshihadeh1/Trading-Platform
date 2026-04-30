import type { SymbolInfo } from '../types';

interface Props {
  symbols: SymbolInfo[];
  loading: boolean;
  newSymbol: string;
  setNewSymbol: (v: string) => void;
  onAdd: () => void;
  onRemove: (id: number) => void;
  onSelect: (sym: SymbolInfo) => void;
  activeSymbolId: number | null;
}

export function Sidebar({ symbols, loading, newSymbol, setNewSymbol, onAdd, onRemove, onSelect, activeSymbolId }: Props) {
  const hyperliquidSymbols = symbols.filter(s => s.exchange === 'hyperliquid');
  const yahooSymbols = symbols.filter(s => s.exchange === 'yahoo');

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') onAdd();
  };

  const renderGroup = (title: string, items: SymbolInfo[]) => {
    if (items.length === 0) return null;
    return (
      <div className="mb-4">
        <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">{title}</h3>
        <div className="space-y-1">
          {items.map(sym => (
            <div
              key={sym.symbol_id}
              onClick={() => onSelect(sym)}
              className={`flex items-center justify-between px-3 py-2 rounded cursor-pointer transition-colors ${
                sym.symbol_id === activeSymbolId
                  ? 'bg-blue-900/50 text-blue-200'
                  : 'hover:bg-dark-700 text-gray-300'
              }`}
            >
              <div>
                <div className="font-medium text-sm">{sym.symbol}</div>
                <div className="text-xs text-gray-500">{sym.display_name}</div>
              </div>
              <button
                onClick={(e) => { e.stopPropagation(); onRemove(sym.symbol_id); }}
                className="text-gray-600 hover:text-red-400 text-xs ml-2"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <div className="w-72 bg-dark-800 border-r border-dark-600 flex flex-col h-full">
      <div className="p-4 border-b border-dark-600">
        <h1 className="text-lg font-bold text-white mb-1">📈 Trading Platform</h1>
        <p className="text-xs text-gray-500">AI-powered decision support</p>
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {loading && <div className="text-center text-gray-500 py-8">Loading...</div>}

        <div>
          <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Add Symbol</h3>
          <div className="flex gap-2 mb-4">
            <input
              type="text"
              value={newSymbol}
              onChange={e => setNewSymbol(e.target.value.toUpperCase())}
              onKeyDown={handleKeyDown}
              placeholder="e.g. BTC, ETH, SPY"
              className="flex-1 bg-dark-700 border border-dark-600 rounded px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500"
            />
            <button
              onClick={onAdd}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm font-medium transition-colors"
            >
              Add
            </button>
          </div>
        </div>

        {renderGroup('Hyperliquid Perps', hyperliquidSymbols)}
        {renderGroup('Stocks / ETFs / Crypto', yahooSymbols)}
        {symbols.length === 0 && !loading && (
          <p className="text-gray-500 text-sm text-center py-4">
            No symbols yet. Add one above!
          </p>
        )}
      </div>

      <div className="p-3 border-t border-dark-600 text-xs text-gray-600">
        Signals refresh every 4h • Trades every 30s
      </div>
    </div>
  );
}
