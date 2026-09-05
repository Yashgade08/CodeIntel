import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  GitPullRequest,
  TrendingUp,
  Loader2,
} from 'lucide-react';
import Markdown from 'markdown-to-jsx';
import { apiService } from '../services/apiService';
import { RiskLevelBadge } from '../components/common/Badge';

export const PrReviewPage: React.FC = () => {
  const { id = 'repo-fastapi-backend' } = useParams<{ id: string }>();
  const [activeTab, setActiveTab] = useState<'summary' | 'smells' | 'security'>('summary');

  const { data: prReview, isLoading } = useQuery({
    queryKey: ['prReview', id],
    queryFn: () => apiService.getPrReview('pr-42'),
  });

  if (isLoading || !prReview) {
    return (
      <div className="flex items-center justify-center h-64 text-xs font-mono text-cyan-400 animate-pulse">
        <Loader2 className="h-5 w-5 animate-spin mr-2" /> Running automated PR diff review pipeline...
      </div>
    );
  }

  return (
    <div className="space-y-8 pb-10">
      {/* Header Banner */}
      <div className="glass-panel p-6 rounded-3xl border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-3">
              <div className="p-2.5 rounded-2xl bg-gradient-to-tr from-cyan-600 to-indigo-600 text-white shadow-lg shadow-cyan-500/20">
                <GitPullRequest className="h-6 w-6" />
              </div>
              <div>
                <span className="text-xs font-mono text-cyan-400 font-bold uppercase tracking-wider">
                  Automated Pull Request Review
                </span>
                <h1 className="text-xl sm:text-2xl font-extrabold text-slate-100 tracking-tight">{prReview.title}</h1>
              </div>
            </div>
            <div className="flex items-center space-x-3 text-xs font-mono text-slate-400 pt-1">
              <span>Author: @{prReview.author}</span>
              <span>•</span>
              <span>Diff: {prReview.diff_summary}</span>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <div className="px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 font-mono text-xs flex items-center space-x-2">
              <TrendingUp className="h-4 w-4 text-amber-400" />
              <span className="text-slate-400">Risk Score Delta:</span>
              <span className="text-rose-400 font-extrabold">+{prReview.risk_score_delta} pts</span>
            </div>
            <RiskLevelBadge level={prReview.risk_level} />
          </div>
        </div>

        {/* Tab Selection Row */}
        <div className="flex items-center space-x-2 border-t border-slate-900 pt-4">
          <button
            onClick={() => setActiveTab('summary')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all ${
              activeTab === 'summary'
                ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            Review Summary
          </button>
          <button
            onClick={() => setActiveTab('smells')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center space-x-1.5 ${
              activeTab === 'smells'
                ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            <span>Code Smells</span>
            <span className="px-1.5 py-0.2 rounded-full bg-slate-950 text-cyan-300 text-[10px]">
              {prReview.code_smells.length}
            </span>
          </button>
          <button
            onClick={() => setActiveTab('security')}
            className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center space-x-1.5 ${
              activeTab === 'security'
                ? 'bg-cyan-500 text-slate-950 shadow-md shadow-cyan-500/20'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            <span>Security Findings</span>
            <span className="px-1.5 py-0.2 rounded-full bg-slate-950 text-amber-400 text-[10px]">
              {prReview.security_findings.length}
            </span>
          </button>
        </div>
      </div>

      {/* Tab Panels */}
      <div className="glass-panel p-6 rounded-3xl border border-slate-800">
        {activeTab === 'summary' && (
          <div className="prose prose-invert prose-xs max-w-none space-y-4">
            <Markdown>{prReview.summary_markdown}</Markdown>
          </div>
        )}

        {activeTab === 'smells' && (
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-slate-100 mb-2">Identified Code Smells & Refactoring Targets</h3>
            {prReview.code_smells.map((smell, idx) => (
              <div key={idx} className="p-4 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-1">
                <div className="flex items-center justify-between font-mono text-xs">
                  <span className="text-cyan-300 font-bold">{smell.file}{smell.line && `#L${smell.line}`}</span>
                  <span className="text-amber-400 font-bold">[{smell.severity}]</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">{smell.issue}</p>
              </div>
            ))}
          </div>
        )}

        {activeTab === 'security' && (
          <div className="space-y-3">
            <h3 className="text-sm font-bold text-slate-100 mb-2">Security Considerations</h3>
            {prReview.security_findings.map((sec, idx) => (
              <div key={idx} className="p-4 rounded-2xl bg-rose-950/30 border border-rose-900/50 space-y-1">
                <div className="flex items-center justify-between font-mono text-xs">
                  <span className="text-rose-300 font-bold">{sec.file}</span>
                  <span className="text-rose-400 font-bold">[{sec.severity}]</span>
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">{sec.description}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
