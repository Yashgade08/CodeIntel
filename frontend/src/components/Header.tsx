import React from 'react';
import { Link } from 'react-router-dom';
import { HealthBadge } from './HealthBadge';
import { Cpu, Github, LayoutDashboard, Search, MessageSquare, Shield, GitBranch } from 'lucide-react';

export const Header: React.FC = () => {
  return (
    <header className="sticky top-0 z-50 bg-slate-950/90 backdrop-blur-md border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-tr from-blue-600 via-indigo-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/20 group-hover:scale-105 transition-transform">
              <Cpu className="w-5 h-5 text-white" />
            </div>
            <div>
              <span className="text-lg font-bold bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
                CodeIntel
              </span>
              <span className="text-xs text-blue-400 block -mt-1 font-mono">Repo Intelligence</span>
            </div>
          </Link>

          {/* Nav links */}
          <nav className="hidden md:flex items-center space-x-1 text-sm font-medium text-slate-300">
            <Link to="/dashboard" className="flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-slate-800/60 hover:text-white transition">
              <LayoutDashboard className="w-4 h-4 text-blue-400" />
              <span>Dashboard</span>
            </Link>
            <span className="text-slate-700">|</span>
            <span className="flex items-center space-x-1 px-3 py-1.5 text-xs text-slate-500 bg-slate-900 rounded-md border border-slate-800" title="Available upon repository ingestion">
              <MessageSquare className="w-3.5 h-3.5" />
              <span>Q&A</span>
            </span>
            <span className="flex items-center space-x-1 px-3 py-1.5 text-xs text-slate-500 bg-slate-900 rounded-md border border-slate-800" title="Available upon repository ingestion">
              <Search className="w-3.5 h-3.5" />
              <span>Search</span>
            </span>
            <span className="flex items-center space-x-1 px-3 py-1.5 text-xs text-slate-500 bg-slate-900 rounded-md border border-slate-800" title="Available upon repository ingestion">
              <GitBranch className="w-3.5 h-3.5" />
              <span>Graph</span>
            </span>
            <span className="flex items-center space-x-1 px-3 py-1.5 text-xs text-slate-500 bg-slate-900 rounded-md border border-slate-800" title="Available upon repository ingestion">
              <Shield className="w-3.5 h-3.5" />
              <span>Risk</span>
            </span>
          </nav>

          {/* Right side items */}
          <div className="flex items-center space-x-4">
            <HealthBadge />
            <a
              href="https://github.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-slate-400 hover:text-white transition p-2 hover:bg-slate-800 rounded-lg"
            >
              <Github className="w-5 h-5" />
            </a>
          </div>
        </div>
      </div>
    </header>
  );
};
