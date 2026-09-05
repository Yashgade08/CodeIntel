import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  Star,
  GitFork,
  FileCode,
  Code2,
  Boxes,
  Activity,
  ShieldCheck,
  CircleDot,
  GitPullRequest,
  ArrowUpRight,
  MessageSquareCode,
  FolderTree,
  ExternalLink,
} from 'lucide-react';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts';
import { apiService } from '../services/apiService';
import { RiskLevelBadge } from '../components/common/Badge';

const LANGUAGE_COLORS: Record<string, string> = {
  Python: '#3572A5',
  TypeScript: '#3178C6',
  JavaScript: '#F1E05A',
  HTML: '#E34C26',
  CSS: '#563D7C',
  SQL: '#e38c00',
  Go: '#00ADD8',
  Rust: '#dea584',
};

export const DashboardPage: React.FC = () => {
  const { id = 'repo-fastapi-backend' } = useParams<{ id: string }>();

  const { data: repo, isLoading: isLoadingRepo } = useQuery({
    queryKey: ['repository', id],
    queryFn: () => apiService.getRepository(id),
  });

  const { data: issues } = useQuery({
    queryKey: ['issues', id],
    queryFn: () => apiService.getIssues(id),
  });

  const { data: riskSummary } = useQuery({
    queryKey: ['riskSummary', id],
    queryFn: () => apiService.getRiskSummary(id),
  });

  if (isLoadingRepo || !repo) {
    return (
      <div className="space-y-6 animate-pulse py-8">
        <div className="h-28 rounded-2xl glass-panel" />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 rounded-2xl glass-panel" />
          ))}
        </div>
      </div>
    );
  }

  const languageData = Object.entries(repo.languages || { Python: 885000, HTML: 24000, JavaScript: 15000 }).map(
    ([name, value]) => ({ name, value })
  );

  const issueList = issues || [];
  const bugCount = issueList.filter((i) => i.category === 'Bug').length;
  const featureCount = issueList.filter((i) => i.category === 'Feature Request').length;
  const criticalCount = issueList.filter((i) => i.severity === 'CRITICAL' || i.severity === 'HIGH').length;

  return (
    <div className="space-y-8 pb-10">
      {/* Header Repository Banner */}
      <div className="glass-panel p-6 sm:p-8 rounded-3xl border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center space-x-3">
              <h1 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
                {repo.owner} / <span className="text-cyan-400">{repo.name}</span>
              </h1>
              <a
                href={repo.github_url}
                target="_blank"
                rel="noreferrer"
                className="p-1.5 rounded-lg bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800 transition-colors"
              >
                <ExternalLink className="h-4 w-4" />
              </a>
            </div>
            <p className="text-xs sm:text-sm text-slate-400 max-w-3xl">{repo.description}</p>
          </div>

          <div className="flex items-center space-x-3">
            <Link
              to={`/repositories/${repo.id}/chat`}
              className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-slate-950 font-bold text-xs flex items-center space-x-2 transition-all shadow-md shadow-cyan-500/20"
            >
              <MessageSquareCode className="h-4 w-4" />
              <span>Ask AI Chat</span>
            </Link>

            <Link
              to={`/repositories/${repo.id}/explorer`}
              className="px-4 py-2 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-700 font-bold text-xs flex items-center space-x-2 transition-all"
            >
              <FolderTree className="h-4 w-4 text-cyan-400" />
              <span>Code Explorer</span>
            </Link>
          </div>
        </div>

        {/* Telemetry Stats Bar */}
        <div className="grid grid-cols-2 sm:grid-cols-6 gap-3 pt-4 border-t border-slate-900 text-center font-mono">
          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">GitHub Stars</div>
            <div className="text-sm font-bold text-amber-400 flex items-center justify-center space-x-1 mt-0.5">
              <Star className="h-3.5 w-3.5 fill-amber-400" />
              <span>{repo.star_count.toLocaleString()}</span>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">GitHub Forks</div>
            <div className="text-sm font-bold text-slate-200 flex items-center justify-center space-x-1 mt-0.5">
              <GitFork className="h-3.5 w-3.5 text-slate-400" />
              <span>{repo.fork_count.toLocaleString()}</span>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Source Files</div>
            <div className="text-sm font-bold text-cyan-400 flex items-center justify-center space-x-1 mt-0.5">
              <FileCode className="h-3.5 w-3.5 text-cyan-400" />
              <span>{repo.file_count || 248}</span>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Functions</div>
            <div className="text-sm font-bold text-indigo-300 flex items-center justify-center space-x-1 mt-0.5">
              <Code2 className="h-3.5 w-3.5 text-indigo-400" />
              <span>{(repo.function_count || 1420).toLocaleString()}</span>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Classes</div>
            <div className="text-sm font-bold text-purple-300 flex items-center justify-center space-x-1 mt-0.5">
              <Boxes className="h-3.5 w-3.5 text-purple-400" />
              <span>{repo.class_count || 310}</span>
            </div>
          </div>

          <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800/80">
            <div className="text-[10px] text-slate-500 uppercase tracking-wider">Total LOC</div>
            <div className="text-sm font-bold text-slate-200 mt-0.5">
              {(repo.total_loc || 42500).toLocaleString()}
            </div>
          </div>
        </div>
      </div>

      {/* Main Intelligence Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column (2 span): Health, Issues, Risk cards */}
        <div className="lg:col-span-2 space-y-6">
          {/* Health & Risk Metrics Overview */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
            {/* Health Score Gauge Card */}
            <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Repository Health</span>
                <Activity className="h-4 w-4 text-emerald-400" />
              </div>

              <div className="flex items-end justify-between">
                <div>
                  <div className="text-4xl font-extrabold text-white">{repo.health_score || 92}%</div>
                  <div className="text-xs text-slate-400 mt-1">Calculated from AST metrics & test coverage</div>
                </div>

                <div className="w-16 h-16 rounded-full border-4 border-emerald-500/20 border-t-emerald-500 flex items-center justify-center text-xs font-bold font-mono text-emerald-400">
                  GREAT
                </div>
              </div>
            </div>

            {/* Overall Code Risk Level */}
            <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">Average Code Risk</span>
                <ShieldCheck className="h-4 w-4 text-amber-400" />
              </div>

              <div className="flex items-end justify-between">
                <div>
                  <div className="text-4xl font-extrabold text-white">{riskSummary?.average_risk_score || 34}/100</div>
                  <div className="text-xs text-slate-400 mt-1">XGBoost ML Risk Score</div>
                </div>

                <RiskLevelBadge level="LOW" score={riskSummary?.average_risk_score || 34} />
              </div>
            </div>
          </div>

          {/* Issue Intelligence Summary Card */}
          <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <CircleDot className="h-5 w-5 text-cyan-400" />
                <h3 className="text-base font-bold text-slate-100">ML Issue Analytics Summary</h3>
              </div>
              <Link
                to={`/repositories/${repo.id}/issues`}
                className="text-xs font-semibold text-cyan-400 hover:underline flex items-center space-x-1"
              >
                <span>View all issues</span>
                <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800/80 space-y-1">
                <div className="text-xs text-slate-400">Total Open Issues</div>
                <div className="text-2xl font-bold text-slate-100">{issueList.length}</div>
              </div>

              <div className="p-4 rounded-xl bg-rose-950/30 border border-rose-900/50 space-y-1">
                <div className="text-xs text-rose-400">Bugs Identified</div>
                <div className="text-2xl font-bold text-rose-300">{bugCount}</div>
              </div>

              <div className="p-4 rounded-xl bg-purple-950/30 border border-purple-900/50 space-y-1">
                <div className="text-xs text-purple-400">Feature Requests</div>
                <div className="text-2xl font-bold text-purple-300">{featureCount}</div>
              </div>

              <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-900/50 space-y-1">
                <div className="text-xs text-amber-400">Critical / High Severity</div>
                <div className="text-2xl font-bold text-amber-300">{criticalCount}</div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column (1 span): Languages breakdown + Navigation Shortcuts */}
        <div className="space-y-6">
          {/* Languages Pie Chart */}
          <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-4">
            <h3 className="text-base font-bold text-slate-100">Languages Breakdown</h3>

            <div className="h-44 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={languageData}
                    cx="50%"
                    cy="50%"
                    innerRadius={45}
                    outerRadius={70}
                    paddingAngle={4}
                    dataKey="value"
                  >
                    {languageData.map((entry) => (
                      <Cell key={entry.name} fill={LANGUAGE_COLORS[entry.name] || '#06b6d4'} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                    itemStyle={{ color: '#f8fafc', fontSize: '12px' }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </div>

            <div className="flex flex-wrap gap-2 text-xs font-mono">
              {languageData.map((lang) => (
                <div key={lang.name} className="flex items-center space-x-1.5 px-2 py-1 rounded bg-slate-900 border border-slate-800">
                  <span
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: LANGUAGE_COLORS[lang.name] || '#06b6d4' }}
                  />
                  <span className="text-slate-300">{lang.name}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Quick Action Navigation Grid */}
          <div className="glass-panel p-6 rounded-2xl border border-slate-800 space-y-3">
            <h3 className="text-sm font-bold text-slate-300 uppercase tracking-wider">Quick Actions</h3>

            <div className="space-y-2">
              <Link
                to={`/repositories/${repo.id}/graph`}
                className="flex items-center justify-between p-3 rounded-xl bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800 text-xs font-semibold text-slate-200 transition-colors"
              >
                <div className="flex items-center space-x-2">
                  <GitFork className="h-4 w-4 text-purple-400" />
                  <span>Inspect Dependency Graph</span>
                </div>
                <ArrowUpRight className="h-3.5 w-3.5 text-slate-500" />
              </Link>

              <Link
                to={`/repositories/${repo.id}/risk`}
                className="flex items-center justify-between p-3 rounded-xl bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800 text-xs font-semibold text-slate-200 transition-colors"
              >
                <div className="flex items-center space-x-2">
                  <ShieldCheck className="h-4 w-4 text-amber-400" />
                  <span>View High Risk Files & SHAP</span>
                </div>
                <ArrowUpRight className="h-3.5 w-3.5 text-slate-500" />
              </Link>

              <Link
                to={`/repositories/${repo.id}/pr-review`}
                className="flex items-center justify-between p-3 rounded-xl bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800 text-xs font-semibold text-slate-200 transition-colors"
              >
                <div className="flex items-center space-x-2">
                  <GitPullRequest className="h-4 w-4 text-cyan-400" />
                  <span>Automated PR Diff Review</span>
                </div>
                <ArrowUpRight className="h-3.5 w-3.5 text-slate-500" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
