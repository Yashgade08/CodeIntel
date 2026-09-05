import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Editor from '@monaco-editor/react';
import {
  FileCode,
  Folder,
  ShieldCheck,
  GitFork,
  Loader2,
} from 'lucide-react';
import { apiService } from '../services/apiService';
import { RiskLevelBadge } from '../components/common/Badge';

export const ExplorerPage: React.FC = () => {
  const { id = 'repo-fastapi-backend' } = useParams<{ id: string }>();
  const [selectedFile, setSelectedFile] = useState<string>('app/rag/pipeline.py');

  const { data: files = [], isLoading: isLoadingFiles } = useQuery({
    queryKey: ['repositoryFiles', id],
    queryFn: () => apiService.getRepositoryFiles(id),
  });

  const { data: fileContent = '', isLoading: isLoadingContent } = useQuery({
    queryKey: ['fileContent', id, selectedFile],
    queryFn: () => apiService.getFileContent(id, selectedFile),
  });

  const { data: fileRisk } = useQuery({
    queryKey: ['fileRisk', id, selectedFile],
    queryFn: () => apiService.getFileRisk(id, selectedFile),
  });

  const { data: impact } = useQuery({
    queryKey: ['fileImpact', id, selectedFile],
    queryFn: () => apiService.getFileDependencies(id, selectedFile),
  });

  const getLanguage = (path: string) => {
    if (path.endsWith('.py')) return 'python';
    if (path.endsWith('.ts') || path.endsWith('.tsx')) return 'typescript';
    if (path.endsWith('.js') || path.endsWith('.jsx')) return 'javascript';
    if (path.endsWith('.json')) return 'json';
    if (path.endsWith('.md')) return 'markdown';
    return 'python';
  };

  return (
    <div className="flex flex-col h-[calc(100vh-140px)] space-y-4">
      {/* Explorer Top Status Header */}
      <div className="flex items-center justify-between glass-panel p-3.5 rounded-2xl border border-slate-800">
        <div className="flex items-center space-x-3 truncate">
          <FileCode className="h-5 w-5 text-cyan-400 flex-shrink-0" />
          <div className="truncate">
            <h1 className="text-sm font-bold text-slate-100 font-mono truncate">{selectedFile}</h1>
            <div className="flex items-center space-x-3 text-[11px] text-slate-400 font-mono mt-0.5">
              <span>Lines: {fileRisk?.line_count || 420}</span>
              <span>•</span>
              <span>Complexity: {fileRisk?.cyclomatic_complexity || 28}</span>
              <span>•</span>
              <span>Dependencies: {impact?.dependencies.length || 2}</span>
            </div>
          </div>
        </div>

        <div className="flex items-center space-x-3 flex-shrink-0">
          <RiskLevelBadge level={fileRisk?.risk_level || 'HIGH'} score={fileRisk?.risk_score || 84} />
        </div>
      </div>

      {/* Main Split Grid */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 min-h-0">
        {/* Left Directory Tree (3 cols) */}
        <div className="lg:col-span-3 glass-panel rounded-2xl border border-slate-800 p-3 overflow-y-auto flex flex-col space-y-2">
          <div className="flex items-center justify-between px-2 py-1 text-xs font-bold uppercase tracking-wider text-slate-400 border-b border-slate-900 pb-2">
            <span className="flex items-center space-x-1.5">
              <Folder className="h-4 w-4 text-cyan-400" />
              <span>Repository Files ({files.length})</span>
            </span>
          </div>

          {isLoadingFiles ? (
            <div className="flex items-center justify-center p-6 text-xs text-slate-500 font-mono animate-pulse">
              <Loader2 className="h-4 w-4 animate-spin mr-2" /> Loading file tree...
            </div>
          ) : (
            <div className="space-y-1 pt-1 font-mono text-xs">
              {files.map((file) => {
                const isSelected = selectedFile === file.path;
                return (
                  <button
                    key={file.id || file.path}
                    onClick={() => setSelectedFile(file.path)}
                    className={`w-full flex items-center justify-between p-2 rounded-lg text-left transition-all ${
                      isSelected
                        ? 'bg-cyan-950/80 text-cyan-300 border border-cyan-800/80 font-semibold'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/60'
                    }`}
                  >
                    <div className="flex items-center space-x-2 truncate">
                      <FileCode className={`h-3.5 w-3.5 ${isSelected ? 'text-cyan-400' : 'text-slate-500'}`} />
                      <span className="truncate">{file.path}</span>
                    </div>
                    {file.risk_level && (
                      <span
                        className={`text-[9px] px-1.5 py-0.2 font-bold rounded ${
                          file.risk_level === 'HIGH'
                            ? 'bg-rose-950 text-rose-400'
                            : file.risk_level === 'MEDIUM'
                            ? 'bg-amber-950 text-amber-400'
                            : 'bg-emerald-950 text-emerald-400'
                        }`}
                      >
                        {file.risk_score || 20}
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          )}
        </div>

        {/* Center Monaco Editor (6 cols) */}
        <div className="lg:col-span-6 glass-panel rounded-2xl border border-slate-800 overflow-hidden flex flex-col">
          <div className="px-4 py-2 bg-slate-950/90 border-b border-slate-900 text-xs font-mono text-slate-400 flex items-center justify-between">
            <span>Editor • {getLanguage(selectedFile)}</span>
            <span className="text-[11px] text-cyan-400">Read-Only View</span>
          </div>

          <div className="flex-1 relative">
            {isLoadingContent ? (
              <div className="absolute inset-0 flex items-center justify-center bg-slate-950 text-xs font-mono text-cyan-400">
                <Loader2 className="h-5 w-5 animate-spin mr-2" /> Loading content...
              </div>
            ) : (
              <Editor
                height="100%"
                language={getLanguage(selectedFile)}
                theme="vs-dark"
                value={fileContent}
                options={{
                  readOnly: true,
                  minimap: { enabled: true },
                  fontSize: 12,
                  scrollBeyondLastLine: false,
                  smoothScrolling: true,
                  fontFamily: 'Consolas, Monaco, "Courier New", monospace',
                }}
              />
            )}
          </div>
        </div>

        {/* Right Telemetry & Symbols Drawer (3 cols) */}
        <div className="lg:col-span-3 glass-panel rounded-2xl border border-slate-800 p-4 overflow-y-auto space-y-5">
          {/* File ML Risk Factor Box */}
          <div className="space-y-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
              <ShieldCheck className="h-4 w-4 text-amber-400" />
              <span>Risk Factors (SHAP)</span>
            </h3>

            <div className="space-y-2">
              {fileRisk?.top_factors?.slice(0, 3).map((factor, idx) => (
                <div key={idx} className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800 text-xs space-y-1">
                  <div className="flex items-center justify-between font-semibold text-slate-200">
                    <span>{factor.feature_name}</span>
                    <span className="text-amber-400 font-mono">+{factor.impact_score}%</span>
                  </div>
                  <p className="text-[11px] text-slate-400 leading-normal">{factor.description}</p>
                </div>
              )) || (
                <div className="text-xs text-slate-500 font-mono">No critical risk factors flagged</div>
              )}
            </div>
          </div>

          {/* Module Dependencies */}
          <div className="space-y-2 pt-2 border-t border-slate-900">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 flex items-center space-x-1.5">
              <GitFork className="h-4 w-4 text-purple-400" />
              <span>Module Dependencies</span>
            </h3>

            <div className="space-y-1 text-xs font-mono">
              <div className="text-[11px] text-slate-500">Imports ({impact?.dependencies.length || 0}):</div>
              {impact?.dependencies.map((dep, idx) => (
                <div key={idx} className="p-1.5 rounded bg-slate-900/60 border border-slate-800 text-cyan-300 truncate">
                  {dep}
                </div>
              ))}

              <div className="text-[11px] text-slate-500 pt-2">Imported By ({impact?.dependents.length || 0}):</div>
              {impact?.dependents.map((dep, idx) => (
                <div key={idx} className="p-1.5 rounded bg-slate-900/60 border border-slate-800 text-indigo-300 truncate">
                  {dep}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
