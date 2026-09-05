import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  ShieldAlert,
  FileCode,
  Info,
  Sliders,
} from 'lucide-react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts';
import { apiService } from '../services/apiService';
import { RiskLevelBadge } from '../components/common/Badge';

export const RiskPage: React.FC = () => {
  const { id = 'repo-fastapi-backend' } = useParams<{ id: string }>();

  const { data: riskSummary } = useQuery({
    queryKey: ['riskSummary', id],
    queryFn: () => apiService.getRiskSummary(id),
  });

  const highRiskFiles = riskSummary?.high_risk_files || [];
  const [selectedFile, setSelectedFile] = useState(highRiskFiles[0] || null);

  const activeFile = selectedFile || highRiskFiles[0];

  const chartData = highRiskFiles.map((f) => ({
    name: f.file.split('/').pop(),
    score: f.risk_score,
    complexity: f.cyclomatic_complexity,
  }));

  return (
    <div className="space-y-8 pb-10">
      {/* Header Banner */}
      <div className="glass-panel p-6 rounded-3xl border border-slate-800 space-y-3">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-2xl bg-gradient-to-tr from-amber-600 to-rose-600 text-white shadow-lg shadow-amber-500/20">
            <ShieldAlert className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-extrabold text-slate-100 tracking-tight flex items-center space-x-2">
              <span>Code Risk & Maintenance Intelligence</span>
              <span className="px-2 py-0.5 text-[10px] uppercase font-bold bg-amber-950 text-amber-400 border border-amber-800 rounded-full">
                XGBoost + SHAP Explainability
              </span>
            </h1>
            <p className="text-xs text-slate-400">Predicting high-maintenance software risk from LOC, cyclomatic complexity, churn & contributors</p>
          </div>
        </div>

        {/* Disclaimer Banner */}
        <div className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 text-xs text-slate-400 flex items-start space-x-2">
          <Info className="h-4 w-4 text-cyan-400 flex-shrink-0 mt-0.5" />
          <span>
            <strong>Engineering Disclaimer:</strong> This model measures code maintainability and refactoring risk based on software complexity features. It does not certify security vulnerability exploits.
          </span>
        </div>
      </div>

      {/* Main Risk Matrix Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* High Risk File Table (7 cols) */}
        <div className="lg:col-span-7 space-y-6">
          <div className="glass-panel rounded-2xl border border-slate-800 overflow-hidden space-y-4 p-5">
            <div className="flex items-center justify-between">
              <h2 className="text-base font-bold text-slate-100 flex items-center space-x-2">
                <FileCode className="h-4 w-4 text-rose-400" />
                <span>High Risk Code Files</span>
              </h2>
              <span className="text-xs font-mono text-slate-400">Sorted by ML Risk Score</span>
            </div>

            {/* Risk Score Distribution Chart */}
            <div className="h-48 w-full pt-2">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <XAxis dataKey="name" stroke="#64748b" fontSize={11} />
                  <YAxis stroke="#64748b" fontSize={11} domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px' }}
                    itemStyle={{ color: '#f8fafc', fontSize: '12px' }}
                  />
                  <Bar dataKey="score" radius={[6, 6, 0, 0]}>
                    {chartData.map((entry, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={entry.score > 75 ? '#f43f5e' : entry.score > 50 ? '#f59e0b' : '#10b981'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Table Rows */}
            <div className="divide-y divide-slate-900 border-t border-slate-900 pt-2">
              {highRiskFiles.map((file) => {
                const isSelected = activeFile?.file === file.file;
                return (
                  <div
                    key={file.file}
                    onClick={() => setSelectedFile(file)}
                    className={`p-3.5 rounded-xl cursor-pointer transition-all flex items-center justify-between ${
                      isSelected
                        ? 'bg-amber-950/40 border border-amber-800/80'
                        : 'hover:bg-slate-900/60 border border-transparent'
                    }`}
                  >
                    <div className="space-y-1 truncate">
                      <div className="text-xs font-bold font-mono text-slate-100 truncate">{file.file}</div>
                      <div className="text-[11px] text-slate-400 font-mono flex items-center space-x-3">
                        <span>Lines: {file.line_count}</span>
                        <span>•</span>
                        <span>Complexity: {file.cyclomatic_complexity}</span>
                        <span>•</span>
                        <span>Commits: {file.commit_frequency}</span>
                      </div>
                    </div>

                    <RiskLevelBadge level={file.risk_level} score={file.risk_score} />
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* SHAP Explainability Breakdown Drawer (5 cols) */}
        <div className="lg:col-span-5 glass-panel rounded-2xl border border-slate-800 p-6 space-y-6">
          {activeFile ? (
            <>
              <div className="space-y-2 border-b border-slate-900 pb-4">
                <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Target File</span>
                <h2 className="text-base font-bold text-slate-100 font-mono break-all">{activeFile.file}</h2>
                <div className="flex items-center space-x-3 pt-1">
                  <RiskLevelBadge level={activeFile.risk_level} score={activeFile.risk_score} />
                  <span className="text-xs font-mono text-slate-400">Score: {activeFile.risk_score}/100</span>
                </div>
              </div>

              {/* Feature Telemetry */}
              <div className="grid grid-cols-2 gap-3 text-center font-mono">
                <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="text-[10px] text-slate-500 uppercase">Cyclomatic Complexity</div>
                  <div className="text-base font-bold text-amber-400 mt-0.5">{activeFile.cyclomatic_complexity}</div>
                </div>

                <div className="p-3 rounded-xl bg-slate-900/80 border border-slate-800">
                  <div className="text-[10px] text-slate-500 uppercase">Contributors</div>
                  <div className="text-base font-bold text-cyan-300 mt-0.5">{activeFile.num_contributors}</div>
                </div>
              </div>

              {/* SHAP Factor Breakdown List */}
              <div className="space-y-3">
                <h3 className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center space-x-1.5">
                  <Sliders className="h-4 w-4" />
                  <span>SHAP Risk Contribution Factors</span>
                </h3>

                <div className="space-y-2">
                  {activeFile.top_factors?.map((factor, idx) => (
                    <div key={idx} className="p-3 rounded-xl bg-slate-900/90 border border-slate-800 space-y-1">
                      <div className="flex items-center justify-between text-xs font-semibold text-slate-200">
                        <span>{factor.feature_name}</span>
                        <span className="text-amber-400 font-mono">+{factor.impact_score}% impact</span>
                      </div>
                      <p className="text-[11px] text-slate-400 leading-normal">{factor.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="text-center text-xs text-slate-500 font-mono py-12">
              Select a file to inspect SHAP feature attribution
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
