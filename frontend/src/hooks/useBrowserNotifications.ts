import { useEffect, useRef, useState } from 'react';
import type { DailyBrief, Signal, SystemStatus, Trade } from '../types';

interface Options {
  signals: Signal[];
  trades: Trade[];
  dailyBrief: DailyBrief | null;
  systemStatus?: SystemStatus | null;
}

export function useBrowserNotifications({ signals, trades, dailyBrief, systemStatus }: Options) {
  const [permission, setPermission] = useState<NotificationPermission>(
    typeof Notification === 'undefined' ? 'denied' : Notification.permission
  );
  const seenSignalIds = useRef<Set<number>>(new Set());
  const seenTradeStates = useRef<Map<number, string>>(new Map());
  const seenBriefId = useRef<number | null>(null);
  const lastSystemAlert = useRef<Map<string, number>>(new Map());
  const initialized = useRef(false);

  const supported = typeof Notification !== 'undefined';
  const enabled = supported && permission === 'granted';

  const requestPermission = async () => {
    if (!supported) return 'denied' as NotificationPermission;
    const result = await Notification.requestPermission();
    setPermission(result);
    return result;
  };

  const notify = (title: string, body: string, tag = title) => {
    if (!enabled) return;
    try {
      new Notification(title, {
        body,
        icon: '/favicon.ico',
        tag,
      });
    } catch {
      // Ignore notification failures; browsers can block them in some contexts.
    }
  };

  const notifyThrottled = (key: string, title: string, body: string, minIntervalMs = 30 * 60 * 1000) => {
    const now = Date.now();
    const previous = lastSystemAlert.current.get(key) ?? 0;
    if (now - previous < minIntervalMs) return;
    lastSystemAlert.current.set(key, now);
    notify(title, body, key);
  };

  useEffect(() => {
    if (!signals.length && !trades.length && !dailyBrief && !systemStatus) return;

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
          `${signal.confidence}% confidence${signal.setup_type ? ` • ${signal.setup_type}` : ''}`,
          `signal-${signal.id}`
        );
      }
    });

    trades.forEach(trade => {
      const previousStatus = seenTradeStates.current.get(trade.id);
      seenTradeStates.current.set(trade.id, trade.status);
      if (previousStatus === 'open' && trade.status !== 'open') {
        notify(
          `Paper trade closed: ${trade.symbol}`,
          `${trade.status.toUpperCase()} • P&L ${trade.pnl?.toFixed?.(2) ?? trade.pnl ?? 0}`,
          `trade-${trade.id}-${trade.status}`
        );
      }
    });

    if (dailyBrief && seenBriefId.current !== dailyBrief.id) {
      seenBriefId.current = dailyBrief.id;
      notify(
        'Daily trading brief ready',
        `${dailyBrief.market_regime.toUpperCase()} • ${dailyBrief.summary.slice(0, 120)}`,
        `daily-brief-${dailyBrief.id}`
      );
    }

    if (systemStatus) {
      if (systemStatus.data && !systemStatus.data.fresh) {
        const ageMinutes = Math.floor((systemStatus.data.age_seconds ?? 0) / 60);
        notifyThrottled(
          'stale-candles',
          'Trading data may be stale',
          `${systemStatus.data.symbol ?? 'Latest'} candles are ${ageMinutes}m old.`
        );
      }

      if (systemStatus.worker?.status && systemStatus.worker.status !== 'ok') {
        notifyThrottled('worker-unhealthy', 'Trading worker needs attention', `Worker status: ${systemStatus.worker.status}`);
      }

      if (systemStatus.components.llm && systemStatus.components.llm.status !== 'ok') {
        notifyThrottled('llm-unhealthy', 'LLM analysis unavailable', systemStatus.components.llm.message ?? 'LLM health check failed.');
      }

      if (systemStatus.daily_brief && !systemStatus.daily_brief.fresh) {
        notifyThrottled('daily-brief-stale', 'Daily brief missing or stale', 'Generate today’s brief before trading.');
      }
    }
  }, [signals, trades, dailyBrief, systemStatus, enabled]);

  return {
    supported,
    permission,
    enabled,
    requestPermission,
  };
}
