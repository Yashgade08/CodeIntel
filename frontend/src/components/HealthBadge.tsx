import React from 'react';
import { useHealth } from '../hooks/useHealth';
import { Activity, AlertCircle, RefreshCw } from 'lucide-react';

export const HealthBadge: React.FC = () => {
  const { health, readiness, loading, error, refetch } = useHealth();

  if (loading && !health) {
    return (
      <div className="flex items-center space-x-2 text-slate-400 text-xs px-2.5 py-1 rounded-full bg-slate-800/80 border border-slate-700">
        <RefreshCw className="w-3 h-3 animate-spin" />
        <span>Connecting...</span>
      </div>
    );
  }

  if (error || !health) {
    return (
      <div className="flex items-center space-x-2 text-red-400 text-xs px-2.5 py-1 rounded-full bg-red-950/50 border border-red-800/60" title={error || 'Backend offline'}>
        <AlertCircle className="w-3 h-3 text-red-400" />
        <span>Backend Offline</span>
        <button onClick={refetch} className="hover:text-white transition">
          <RefreshCw className="w-2.5 h-2.5" />
        </button>
      </div>
    );
  }

  const isReady = readiness?.status === 'ready';

  return (
    <div className="flex items-center space-x-2 text-xs px-3 py-1 rounded-full bg-slate-900 border border-slate-700/80">
      <span className="relative flex h-2 w-2">
        <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${isReady ? 'bg-emerald-400' : 'bg-amber-400'} opacity-75`}></span>
        <span className={`relative inline-flex rounded-full h-2 w-2 ${isReady ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
      </span>
      <span className="text-slate-300 font-medium">{health.service} v{health.version}</span>
      <span className="text-slate-500">|</span>
      <span className={isReady ? 'text-emerald-400' : 'text-amber-400'}>
        {isReady ? 'API Ready' : 'Degraded'}
      </span>
      <Activity className="w-3 h-3 text-slate-400" />
    </div>
  );
};
