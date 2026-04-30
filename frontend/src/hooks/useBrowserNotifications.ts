import { useEffect, useRef, useState } from 'react';
import type { DailyBrief, Signal, Trade } from '../types';

interface Options {
  signals: Signal[];
  trades: Trade[];
  dailyBrief: DailyBrief | null;
}

export function useBrowserNotifications({ signals, trades, dailyBrief }: Options) {
  const [permission, setPermission] = useState<NotificationPermission>(
    typeof Notification === 'undefined' ? 'denied' : Notification.permission
  );
  const seenSignalIds = useRef<Set<number>>(new Set());
  const seenTradeStates = useRef<Map<number, string>>(new Map());
  const seenBriefId = useRef<number | null>(null);
  const initialized = useRef(false);

  const supported = typeof Notification !== 'undefined';
  const enabled = supported && permission === 'granted';

  const requestPermission = async () => {
    if (!supported) return 'denied' as NotificationPermission;
    const result = await Notification.requestPermission();
    setPermission(result);
    return result;
  };

  const notify = (title: string, body: string) => {
    if (!enabled) return;
    try {
      new Notification(title, {
        body,
        icon: '/favicon.ico',
        tag: title,
      });
    } catch {
      // Ignore notification failures; browsers can block them in some contexts.
    }
  };

  useEffect(() => {
    if (!signals.length && !trades.length && !dailyBrief) return;

    if (!initialized.current) {
      signals.forEach(signal => seenSignalIds.current.add(signal.id));
      trades.forEach(trade => seenTradeStates.current.set(trade.id, trade.status));
      if (dailyBrief) seenBriefId.current = dailyBrief.id;
      initialized.current = true;
      return;
    }

    signals.forEach(signal => {
      if (seenSignalIds.current.has(signal.id)) return;
      seenSignalIds.current.add(signal.id);
      if (signal.confidence >= 75 && signal.direction !== 'hold') {
        notify(
          `${signal.direction.toUpperCase()} signal: ${signal.symbol}`,
          `${signal.confidence}% confidence${signal.setup_type ? ` • ${signal.setup_type}` : ''}`
        );
      }
    });

    trades.forEach(trade => {
      const previousStatus = seenTradeStates.current.get(trade.id);
      seenTradeStates.current.set(trade.id, trade.status);
      if (previousStatus === 'open' && trade.status !== 'open') {
        notify(
          `Paper trade closed: ${trade.symbol}`,
          `${trade.status.toUpperCase()} • P&L ${trade.pnl?.toFixed?.(2) ?? trade.pnl ?? 0}`
        );
      }
    });

    if (dailyBrief && seenBriefId.current !== dailyBrief.id) {
      seenBriefId.current = dailyBrief.id;
      notify('Daily trading brief ready', `${dailyBrief.market_regime.toUpperCase()} • ${dailyBrief.summary.slice(0, 120)}`);
    }
  }, [signals, trades, dailyBrief, enabled]);

  return {
    supported,
    permission,
    enabled,
    requestPermission,
  };
}
