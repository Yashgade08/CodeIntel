import React from 'react';
import type { IssueCategory, IssueSeverity } from '../../types';

interface BadgeProps {
  children: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'danger' | 'info' | 'cyan' | 'purple';
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const Badge: React.FC<BadgeProps> = ({ children, variant = 'default', size = 'md', className = '' }) => {
  const variantStyles = {
    default: 'bg-slate-800 text-slate-300 border-slate-700',
    success: 'bg-emerald-950/70 text-emerald-400 border-emerald-800/60',
    warning: 'bg-amber-950/70 text-amber-400 border-amber-800/60',
    danger: 'bg-rose-950/70 text-rose-400 border-rose-800/60',
    info: 'bg-sky-950/70 text-sky-400 border-sky-800/60',
    cyan: 'bg-cyan-950/70 text-cyan-400 border-cyan-800/60',
    purple: 'bg-purple-950/70 text-purple-400 border-purple-800/60',
  };

  const sizeStyles = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-xs font-medium',
    lg: 'px-3 py-1 text-sm font-semibold',
  };

  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}>
      {children}
    </span>
  );
};

export const CategoryBadge: React.FC<{ category?: IssueCategory }> = ({ category }) => {
  if (!category) return null;
  const config: Record<IssueCategory, { variant: BadgeProps['variant']; icon: string }> = {
    Bug: { variant: 'danger', icon: '🐛' },
    'Feature Request': { variant: 'purple', icon: '✨' },
    Documentation: { variant: 'info', icon: '📝' },
    Question: { variant: 'warning', icon: '❓' },
    Enhancement: { variant: 'cyan', icon: '🚀' },
    Performance: { variant: 'warning', icon: '⚡' },
    Security: { variant: 'danger', icon: '🛡️' },
  };

  const { variant, icon } = config[category] || { variant: 'default', icon: '📌' };
  return (
    <Badge variant={variant} size="sm">
      <span>{icon}</span>
      <span>{category}</span>
    </Badge>
  );
};

export const SeverityBadge: React.FC<{ severity?: IssueSeverity }> = ({ severity }) => {
  if (!severity) return null;
  const config: Record<IssueSeverity, BadgeProps['variant']> = {
    LOW: 'info',
    MEDIUM: 'warning',
    HIGH: 'danger',
    CRITICAL: 'danger',
  };

  return (
    <Badge variant={config[severity]} size="sm" className={severity === 'CRITICAL' ? 'animate-pulse font-bold' : ''}>
      <span>{severity === 'CRITICAL' ? '🚨' : severity === 'HIGH' ? '⚠️' : '🔵'}</span>
      <span>{severity}</span>
    </Badge>
  );
};

export const RiskLevelBadge: React.FC<{ level?: 'LOW' | 'MEDIUM' | 'HIGH'; score?: number }> = ({ level, score }) => {
  if (!level) return null;
  const config = {
    LOW: { variant: 'success' as const, label: 'LOW RISK' },
    MEDIUM: { variant: 'warning' as const, label: 'MEDIUM RISK' },
    HIGH: { variant: 'danger' as const, label: 'HIGH RISK' },
  };

  const current = config[level];
  return (
    <Badge variant={current.variant} size="sm">
      <span>{current.label}</span>
      {score !== undefined && <span className="opacity-75 font-mono">({score}/100)</span>}
    </Badge>
  );
};
