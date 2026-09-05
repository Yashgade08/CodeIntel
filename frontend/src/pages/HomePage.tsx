import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Github,
  ArrowRight,
  ShieldCheck,
  Brain,
  GitFork,
  Sparkles,
  Layers,
  Terminal,
  Star,
  FileCode,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { apiService } from '../services/apiService';
import { RiskLevelBadge } from '../components/common/Badge';

export const HomePage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [githubUrl, setGithubUrl] = useState('https://github.com/tiangolo/fastapi');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const { data: repoData, isLoading: isLoadingRepos } = useQuery({
    queryKey: ['repositories'],
    queryFn: () => apiService.listRepositories(),
  });

  const ingestMutation = useMutation({
    mutationFn: (url: string) => apiService.createRepository(url),
    onSuccess: (newRepo) => {
      queryClient.invalidateQueries({ queryKey: ['repositories'] });
      navigate(`/repositories/${newRepo.id}`);
    },
    onError: (error: Error) => {
      setErrorMessage(error.message || 'Failed to submit repository for ingestion.');
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    if (!githubUrl.trim()) {
      setErrorMessage('Please enter a valid GitHub repository URL.');
      return;
    }
    if (!githubUrl.includes('github.com')) {
      setErrorMessage('URL must be a public GitHub repository link (e.g. https://github.com/owner/repo)');
      return;
    }
    ingestMutation.mutate(githubUrl.trim());
  };

  const repositories = repoData?.repositories || [];

  return (
    <div className="space-y-16 py-6">
      {/* Hero Header Section */}
      <div className="relative text-center max-w-4xl mx-auto space-y-6 pt-4">
        {/* Glow backdrop decorative accent */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-cyan-500/10 blur-[120px] rounded-full -z-10 pointer-events-none" />

        <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-cyan-950/80 border border-cyan-800/80 text-cyan-400 text-xs font-semibold shadow-inner">
          <Sparkles className="h-3.5 w-3.5 text-cyan-400 animate-spin" />
          <span>ML-Powered Codebase & Issue Intelligence Engine</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold tracking-tight text-white leading-tight">
          Deep Analysis for Any <br className="hidden sm:inline" />
          <span className="bg-gradient-to-r from-cyan-400 via-sky-300 to-indigo-400 bg-clip-text text-transparent">
            GitHub Repository
          </span>
        </h1>

        <p className="text-lg text-slate-400 max-w-2xl mx-auto font-normal">
          Classify issues with Logistic Regression, predict software maintenance risk with XGBoost, and query code relationships via NetworkX dependency graphs.
        </p>

        {/* Ingestion Submission Card */}
        <div className="max-w-2xl mx-auto pt-4">
          <form onSubmit={handleSubmit} className="relative group">
            <div className="flex flex-col sm:flex-row items-center p-2 rounded-2xl glass-panel border border-slate-700/80 shadow-2xl focus-within:border-cyan-500/80 focus-within:ring-2 focus-within:ring-cyan-500/20 transition-all gap-2">
              <div className="flex items-center space-x-3 px-3 w-full sm:w-auto flex-1">
                <Github className="h-5 w-5 text-slate-400 flex-shrink-0" />
                <input
                  type="text"
                  value={githubUrl}
                  onChange={(e) => setGithubUrl(e.target.value)}
                  placeholder="https://github.com/owner/repository"
                  className="w-full bg-transparent text-sm text-slate-100 placeholder-slate-500 focus:outline-none py-2"
                />
              </div>

              <button
                type="submit"
                disabled={ingestMutation.isPending}
                className="w-full sm:w-auto px-6 py-3 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-slate-950 font-extrabold text-sm flex items-center justify-center space-x-2 transition-all shadow-lg shadow-cyan-500/25 disabled:opacity-50 whitespace-nowrap cursor-pointer"
              >
                {ingestMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin text-slate-950" />
                    <span>Analyzing...</span>
                  </>
                ) : (
                  <>
                    <span>Analyze Repository</span>
                    <ArrowRight className="h-4 w-4" />
                  </>
                )}
              </button>
            </div>
          </form>

          {errorMessage && (
            <div className="mt-3 flex items-center justify-center space-x-2 text-rose-400 text-xs bg-rose-950/40 border border-rose-900/60 p-2.5 rounded-lg">
              <AlertCircle className="h-4 w-4 flex-shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          <div className="mt-3 flex items-center justify-center space-x-4 text-xs text-slate-500 font-mono">
            <span>Try example:</span>
            <button
              onClick={() => setGithubUrl('https://github.com/tiangolo/fastapi')}
              className="text-cyan-400 hover:underline hover:text-cyan-300 transition-colors"
            >
              tiangolo/fastapi
            </button>
            <span>•</span>
            <button
              onClick={() => setGithubUrl('https://github.com/codeintel/codeintel-core')}
              className="text-cyan-400 hover:underline hover:text-cyan-300 transition-colors"
            >
              codeintel-core
            </button>
          </div>
        </div>
      </div>

      {/* Core Platform Capabilities Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 pt-6">
        <div className="glass-panel glass-panel-hover p-6 rounded-2xl space-y-3 border border-slate-800">
          <div className="p-3 w-fit rounded-xl bg-cyan-950/80 text-cyan-400 border border-cyan-800/80">
            <Brain className="h-6 w-6" />
          </div>
          <h3 className="text-base font-bold text-slate-100">ML Issue Intelligence</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            TF-IDF vectorizer + Logistic Regression model classifies issues into Bug, Feature, Security, Performance & detects semantic duplicates.
          </p>
        </div>

        <div className="glass-panel glass-panel-hover p-6 rounded-2xl space-y-3 border border-slate-800">
          <div className="p-3 w-fit rounded-xl bg-amber-950/80 text-amber-400 border border-amber-800/80">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <h3 className="text-base font-bold text-slate-100">Code Risk Score</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Calculates cyclomatic complexity, churn, contributor count, and line count with SHAP factor explainability for maintainability.
          </p>
        </div>

        <div className="glass-panel glass-panel-hover p-6 rounded-2xl space-y-3 border border-slate-800">
          <div className="p-3 w-fit rounded-xl bg-purple-950/80 text-purple-400 border border-purple-800/80">
            <GitFork className="h-6 w-6" />
          </div>
          <h3 className="text-base font-bold text-slate-100">Dependency DAG</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Extracts AST symbols and constructs NetworkX directed graphs to visualize module dependencies and calculate impact radius.
          </p>
        </div>

        <div className="glass-panel glass-panel-hover p-6 rounded-2xl space-y-3 border border-slate-800">
          <div className="p-3 w-fit rounded-xl bg-indigo-950/80 text-indigo-400 border border-indigo-800/80">
            <Terminal className="h-6 w-6" />
          </div>
          <h3 className="text-base font-bold text-slate-100">RAG Codebase Chat</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Natural language developer assistant retrieving vector chunks and NetworkX AST graph contexts with exact source citations.
          </p>
        </div>
      </div>

      {/* Active Repositories Section */}
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-slate-100 flex items-center space-x-2">
              <Layers className="h-5 w-5 text-cyan-400" />
              <span>Analyzed Repositories</span>
            </h2>
            <p className="text-xs text-slate-400">Select a pre-indexed codebase to inspect telemetry, issues, or graph DAGs</p>
          </div>
        </div>

        {isLoadingRepos ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {[1, 2].map((i) => (
              <div key={i} className="h-44 rounded-2xl glass-panel animate-pulse p-6" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {repositories.map((repo) => (
              <div
                key={repo.id}
                onClick={() => navigate(`/repositories/${repo.id}`)}
                className="glass-panel glass-panel-hover p-6 rounded-2xl border border-slate-800/80 cursor-pointer space-y-4 transition-all"
              >
                <div className="flex items-start justify-between">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-2">
                      <span className="text-base font-bold text-slate-100 hover:text-cyan-400 transition-colors">
                        {repo.owner} / {repo.name}
                      </span>
                      <span className="px-2 py-0.5 text-[10px] uppercase font-bold bg-emerald-950/80 text-emerald-400 border border-emerald-800/80 rounded-full">
                        {repo.ingestion_status}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400 line-clamp-2">{repo.description}</p>
                  </div>
                  <RiskLevelBadge level="LOW" score={repo.average_risk_score || 28} />
                </div>

                <div className="grid grid-cols-4 gap-2 pt-2 border-t border-slate-900 text-center font-mono">
                  <div className="p-2 rounded-lg bg-slate-900/60">
                    <div className="text-[10px] text-slate-500 uppercase">Stars</div>
                    <div className="text-xs font-bold text-slate-200 flex items-center justify-center space-x-1">
                      <Star className="h-3 w-3 text-amber-400 fill-amber-400" />
                      <span>{repo.star_count.toLocaleString()}</span>
                    </div>
                  </div>

                  <div className="p-2 rounded-lg bg-slate-900/60">
                    <div className="text-[10px] text-slate-500 uppercase">Files</div>
                    <div className="text-xs font-bold text-cyan-300 flex items-center justify-center space-x-1">
                      <FileCode className="h-3 w-3 text-cyan-400" />
                      <span>{repo.file_count || 248}</span>
                    </div>
                  </div>

                  <div className="p-2 rounded-lg bg-slate-900/60">
                    <div className="text-[10px] text-slate-500 uppercase">Functions</div>
                    <div className="text-xs font-bold text-indigo-300">
                      {repo.function_count || 1420}
                    </div>
                  </div>

                  <div className="p-2 rounded-lg bg-slate-900/60">
                    <div className="text-[10px] text-slate-500 uppercase">Health</div>
                    <div className="text-xs font-bold text-emerald-400">
                      {repo.health_score || 92}%
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
