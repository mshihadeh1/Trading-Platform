import { useCallback, useEffect, useState } from 'react';

import { system } from '../lib/api';
import type { SystemStatus } from '../types';

export function useSystemStatus() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await system.status();
      setStatus(data);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    }
  }, []);

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, [load]);

  return { status, error, refetch: load };
}
