import { useEffect, useRef, useState } from 'react';

export interface RealtimeSnapshot {
  type: 'snapshot';
  timestamp: string;
  latest_candle: {
    symbol_id: number;
    symbol: string;
    exchange: string;
    timestamp: string | null;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  } | null;
  latest_signal: {
    id: number;
    symbol: string;
    direction: string;
    confidence: number;
    timestamp: string | null;
  } | null;
  open_positions: number;
  unrealized_pnl: number;
}

export function useRealtimeStream() {
  const [connected, setConnected] = useState(false);
  const [snapshot, setSnapshot] = useState<RealtimeSnapshot | null>(null);
  const retryTimer = useRef<number | null>(null);

  useEffect(() => {
    let socket: WebSocket | null = null;
    let shouldReconnect = true;

    const connect = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      socket = new WebSocket(`${protocol}//${window.location.host}/ws/stream`);

      socket.onopen = () => setConnected(true);
      socket.onerror = () => setConnected(false);
      socket.onclose = () => {
        setConnected(false);
        if (shouldReconnect) {
          retryTimer.current = window.setTimeout(connect, 5000);
        }
      };
      socket.onmessage = event => {
        try {
          setSnapshot(JSON.parse(event.data));
        } catch {
          // Ignore malformed websocket messages.
        }
      };
    };

    connect();

    return () => {
      shouldReconnect = false;
      if (retryTimer.current !== null) window.clearTimeout(retryTimer.current);
      socket?.close();
    };
  }, []);

  return { connected, snapshot };
}
