import React from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';
import {
  LayoutDashboard,
  MessageSquareCode,
  FolderTree,
  CircleDot,
  GitFork,
  ShieldAlert,
  GitPullRequest,
  Home,
  ChevronRight,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/apiService';

export const Sidebar: React.FC = () => {
  const location = useLocation();
  const { id: routeRepoId } = useParams<{ id: string }>();

  const { data: repoData } = useQuery({
    queryKey: ['repositories'],
    queryFn: () => apiService.listRepositories(),
  });

  const repositories = repoData?.repositories || [];
  const currentRepoId = routeRepoId || repositories[0]?.id || 'repo-fastapi-backend';
  const currentRepo = repositories.find((r) => r.id === currentRepoId) || repositories[0];

  const navItems = [
    { label: 'Overview', path: `/repositories/${currentRepoId}`, icon: LayoutDashboard },
    { label: 'AI Codebase Chat', path: `/repositories/${currentRepoId}/chat`, icon: MessageSquareCode },
    { label: 'Code Explorer', path: `/repositories/${currentRepoId}/explorer`, icon: FolderTree },
    { label: 'ML Issue Intelligence', path: `/repositories/${currentRepoId}/issues`, icon: CircleDot },
    { label: 'Dependency Graph', path: `/repositories/${currentRepoId}/graph`, icon: GitFork },
    { label: 'Code Risk & SHAP', path: `/repositories/${currentRepoId}/risk`, icon: ShieldAlert },
    { label: 'Automated PR Review', path: `/repositories/${currentRepoId}/pr-review`, icon: GitPullRequest },
    { label: 'System Evaluation', path: `/evaluation`, icon: ShieldAlert },
  ];

  if (location.pathname === '/') return null;

  return (
    <aside className="hidden lg:flex flex-col w-64 glass-panel border-r border-slate-800 bg-slate-950/90 h-[calc(100vh-64px)] sticky top-16 flex-shrink-0 p-4 space-y-6">
      {/* Current Repo Card */}
      <div className="p-3 rounded-2xl bg-slate-900/90 border border-slate-800 space-y-1">
        <div className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Active Repository</div>
        <div className="text-sm font-bold text-slate-100 truncate">{currentRepo?.owner} / {currentRepo?.name}</div>
        <div className="text-[11px] text-cyan-400 font-mono flex items-center space-x-1 pt-0.5">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
          <span>{currentRepo?.ingestion_status || 'Complete'}</span>
        </div>
      </div>

      {/* Navigation Menu */}
      <div className="space-y-1 flex-1">
        <div className="px-2 pb-2 text-[10px] font-bold uppercase tracking-wider text-slate-500">Platform Navigation</div>

        <Link
          to="/"
          className="flex items-center space-x-3 px-3 py-2 rounded-xl text-xs font-semibold text-slate-400 hover:text-slate-200 hover:bg-slate-900/80 transition-all mb-2"
        >
          <Home className="h-4 w-4 text-slate-500" />
          <span>Home / Ingest Repo</span>
        </Link>

        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = location.pathname === item.path;
          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center justify-between px-3 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                isActive
                  ? 'bg-gradient-to-r from-cyan-950/80 to-indigo-950/80 text-cyan-300 border border-cyan-800/80 shadow-md shadow-cyan-500/10'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
              }`}
            >
              <div className="flex items-center space-x-3 truncate">
                <Icon className={`h-4 w-4 ${isActive ? 'text-cyan-400' : 'text-slate-500'}`} />
                <span className="truncate">{item.label}</span>
              </div>
              {isActive && <ChevronRight className="h-3.5 w-3.5 text-cyan-400 flex-shrink-0" />}
            </Link>
          );
        })}
      </div>

      {/* System Telemetry Footer */}
      <div className="p-3 rounded-2xl bg-slate-950 border border-slate-900 space-y-1 text-[11px] font-mono text-slate-500">
        <div className="flex items-center justify-between text-slate-400">
          <span>Backend API</span>
          <span className="text-emerald-400 font-bold">FastAPI</span>
        </div>
        <div className="flex items-center justify-between text-slate-400">
          <span>Vector RAG</span>
          <span className="text-cyan-400 font-bold">ChromaDB</span>
        </div>
        <div className="flex items-center justify-between text-slate-400">
          <span>Graph DAG</span>
          <span className="text-purple-400 font-bold">NetworkX</span>
        </div>
      </div>
    </aside>
  );
};
