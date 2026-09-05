import React from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';
import {
  BrainCircuit,
  LayoutDashboard,
  MessageSquareCode,
  FolderTree,
  CircleDot,
  GitFork,
  ShieldAlert,
  GitPullRequest,
} from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiService } from '../../services/apiService';

export const Header: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { id: routeRepoId } = useParams<{ id: string }>();

  const { data: repoData } = useQuery({
    queryKey: ['repositories'],
    queryFn: () => apiService.listRepositories(),
  });

  const repositories = repoData?.repositories || [];
  const currentRepoId = routeRepoId || repositories[0]?.id || 'repo-fastapi-backend';

  const { data: readiness } = useQuery({
    queryKey: ['readiness'],
    queryFn: () => apiService.getReadiness(),
    refetchInterval: 30000,
  });

  const handleRepoChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const selectedId = e.target.value;
    if (!selectedId) return;

    const currentPath = location.pathname;
    if (currentPath.includes('/chat')) navigate(`/repositories/${selectedId}/chat`);
    else if (currentPath.includes('/explorer')) navigate(`/repositories/${selectedId}/explorer`);
    else if (currentPath.includes('/issues')) navigate(`/repositories/${selectedId}/issues`);
    else if (currentPath.includes('/graph')) navigate(`/repositories/${selectedId}/graph`);
    else if (currentPath.includes('/risk')) navigate(`/repositories/${selectedId}/risk`);
    else if (currentPath.includes('/pr-review')) navigate(`/repositories/${selectedId}/pr-review`);
    else navigate(`/repositories/${selectedId}`);
  };

  const navItems = [
    { label: 'Dashboard', path: `/repositories/${currentRepoId}`, icon: LayoutDashboard },
    { label: 'AI Chat', path: `/repositories/${currentRepoId}/chat`, icon: MessageSquareCode },
    { label: 'Explorer', path: `/repositories/${currentRepoId}/explorer`, icon: FolderTree },
    { label: 'Issues ML', path: `/repositories/${currentRepoId}/issues`, icon: CircleDot },
    { label: 'Dependency Graph', path: `/repositories/${currentRepoId}/graph`, icon: GitFork },
    { label: 'Code Risk', path: `/repositories/${currentRepoId}/risk`, icon: ShieldAlert },
    { label: 'PR Review', path: `/repositories/${currentRepoId}/pr-review`, icon: GitPullRequest },
    { label: 'Evaluation', path: `/evaluation`, icon: ShieldAlert },
  ];

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-slate-800 bg-slate-950/80 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Brand */}
          <div className="flex items-center space-x-6">
            <Link to="/" className="flex items-center space-x-3 group">
              <div className="p-2 rounded-xl bg-gradient-to-tr from-cyan-600 to-indigo-600 text-white shadow-lg shadow-cyan-500/20 group-hover:scale-105 transition-transform">
                <BrainCircuit className="h-6 w-6" />
              </div>
              <div>
                <span className="text-lg font-extrabold tracking-tight bg-gradient-to-r from-slate-100 via-cyan-200 to-indigo-300 bg-clip-text text-transparent">
                  CodeIntel
                </span>
                <span className="hidden sm:inline-block ml-2 px-1.5 py-0.5 text-[10px] uppercase font-bold tracking-widest bg-cyan-950/80 text-cyan-400 border border-cyan-800/60 rounded">
                  v1.0 ML
                </span>
              </div>
            </Link>

            {/* Active Repository Selector */}
            {repositories.length > 0 && location.pathname !== '/' && (
              <div className="hidden lg:flex items-center space-x-2 pl-4 border-l border-slate-800">
                <span className="text-xs text-slate-400">Repo:</span>
                <select
                  value={currentRepoId}
                  onChange={handleRepoChange}
                  className="bg-slate-900 text-xs font-semibold text-slate-200 border border-slate-700 rounded-lg px-2.5 py-1 focus:outline-none focus:border-cyan-500 transition-colors"
                >
                  {repositories.map((repo) => (
                    <option key={repo.id} value={repo.id}>
                      {repo.owner}/{repo.name}
                    </option>
                  ))}
                </select>
              </div>
            )}
          </div>

          {/* Navigation Links */}
          {location.pathname !== '/' && (
            <nav className="hidden md:flex items-center space-x-1">
              {navItems.map((item) => {
                const Icon = item.icon;
                const isActive = location.pathname === item.path;
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      isActive
                        ? 'bg-gradient-to-r from-cyan-500/15 to-indigo-500/15 text-cyan-300 border border-cyan-500/30 shadow-sm shadow-cyan-500/10'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                    }`}
                  >
                    <Icon className={`h-4 w-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                    <span>{item.label}</span>
                  </Link>
                );
              })}
            </nav>
          )}

          {/* Telemetry Status Indicator */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2 px-2.5 py-1 rounded-full bg-slate-900/90 border border-slate-800 text-xs">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="text-slate-300 font-mono text-[11px]">
                {readiness?.status === 'ready' ? 'API Ready' : 'Online'}
              </span>
            </div>

            <Link
              to="/"
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-950 font-bold transition-all shadow-md shadow-cyan-500/20 flex items-center space-x-1.5"
            >
              <span>+ Ingest Repo</span>
            </Link>
          </div>
        </div>

        {/* Mobile Navigation Row */}
        {location.pathname !== '/' && (
          <div className="md:hidden flex items-center space-x-1 overflow-x-auto py-2 border-t border-slate-900 scrollbar-none">
            {navItems.map((item) => {
              const Icon = item.icon;
              const isActive = location.pathname === item.path;
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  className={`flex items-center space-x-1.5 px-2.5 py-1 rounded-md text-xs whitespace-nowrap ${
                    isActive ? 'bg-cyan-950 text-cyan-300 border border-cyan-800' : 'text-slate-400'
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </header>
  );
};
