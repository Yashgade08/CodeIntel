import { useState, useEffect } from 'react';
import { apiService } from '../services/apiService';
import type { HealthCheckResponse, SystemReadinessResponse } from '../types';

export function useHealth() {
  const [health, setHealth] = useState<HealthCheckResponse | null>(null);
  const [readiness, setReadiness] = useState<SystemReadinessResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkHealth = async () => {
    try {
      setLoading(true);
      setError(null);
      const [h, r] = await Promise.all([
        apiService.getHealth(),
        apiService.getReadiness().catch(() => null),
      ]);
      setHealth(h);
      setReadiness(r);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 15000);
    return () => clearInterval(interval);
  }, []);

  return { health, readiness, loading, error, refetch: checkHealth };
}
