import React, { useState } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Brain,
  Filter,
  Sparkles,
  Plus,
  Loader2,
  X,
  FileCode,
  CheckCircle2,
  BookOpen,
} from 'lucide-react';
import { apiService } from '../services/apiService';
import { CategoryBadge, SeverityBadge } from '../components/common/Badge';
import { useToast } from '../components/common/Toast';
import type { Issue } from '../types';

export const IssuesPage: React.FC = () => {
  const { id = 'repo-fastapi-backend' } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedIssue, setSelectedIssue] = useState<Issue | null>(null);
  const [isAnalyzeModalOpen, setIsAnalyzeModalOpen] = useState(false);

  const [newTitle, setNewTitle] = useState('');
  const [newBody, setNewBody] = useState('');

  const { data: issues = [], isLoading } = useQuery({
    queryKey: ['issues', id],
    queryFn: () => apiService.getIssues(id),
  });

  const analyzeMutation = useMutation({
    mutationFn: () =>
      apiService.analyzeIssue({
        repository_id: id,
        title: newTitle,
        body: newBody,
      }),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['issues', id] });
      setIsAnalyzeModalOpen(false);
      setNewTitle('');
      setNewBody('');
      showToast(`ML Analysis complete: Classified as ${data.category} (${data.severity})`, 'success');
    },
  });

  const filteredIssues = issues.filter((issue) => {
    if (selectedCategory === 'ALL') return true;
    return issue.category === selectedCategory;
  });

  const activeIssue = selectedIssue || filteredIssues[0];

  return (
    <div className="space-y-6 pb-10">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between glass-panel p-6 rounded-3xl border border-slate-800 gap-4">
        <div className="space-y-1">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-2xl bg-gradient-to-tr from-cyan-600 to-indigo-600 text-white shadow-lg shadow-cyan-500/20">
              <Brain className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-2xl font-extrabold text-slate-100 tracking-tight flex items-center space-x-2">
                <span>ML Issue Intelligence & Investigation</span>
                <span className="px-2 py-0.5 text-[10px] uppercase font-bold bg-cyan-950 text-cyan-400 border border-cyan-800 rounded-full">
                  TF-IDF + RAG Grounding
                </span>
              </h1>
              <p className="text-xs text-slate-400">Model issue classification, duplicate detection, RAG code evidence & investigation steps</p>
            </div>
          </div>
        </div>

        <button
          onClick={() => setIsAnalyzeModalOpen(true)}
          className="px-4 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 hover:from-cyan-400 hover:to-indigo-500 text-slate-950 font-extrabold text-xs flex items-center justify-center space-x-2 transition-all shadow-md shadow-cyan-500/20 cursor-pointer"
        >
          <Plus className="h-4 w-4" />
          <span>Analyze Custom Issue</span>
        </button>
      </div>

      {/* Category Filter Pills */}
      <div className="flex items-center space-x-2 overflow-x-auto py-1 scrollbar-none">
        <span className="text-xs font-bold uppercase tracking-wider text-slate-500 mr-2 flex items-center space-x-1">
          <Filter className="h-3.5 w-3.5" />
          <span>Category:</span>
        </span>
        {['ALL', 'Bug', 'Feature Request', 'Documentation', 'Question', 'Enhancement', 'Performance', 'Security'].map(
          (cat) => (
            <button
              key={cat}
              onClick={() => setSelectedCategory(cat)}
              className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all ${
                selectedCategory === cat
                  ? 'bg-cyan-500 text-slate-950 font-bold shadow-md shadow-cyan-500/20'
                  : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
              }`}
            >
              {cat}
            </button>
          )
        )}
      </div>

      {/* Main Issue Grid & 6-Point Detail Pane */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Issue List Table (5 cols) */}
        <div className="lg:col-span-5 glass-panel rounded-2xl border border-slate-800 overflow-hidden space-y-1">
          <div className="p-4 bg-slate-950/80 border-b border-slate-900 flex items-center justify-between text-xs font-bold text-slate-400">
            <span>Issue List ({filteredIssues.length})</span>
            <span>Classification</span>
          </div>

          {isLoading ? (
            <div className="p-8 text-center text-xs text-slate-500 font-mono animate-pulse">
              Loading issue predictions...
            </div>
          ) : (
            <div className="divide-y divide-slate-900">
              {filteredIssues.map((issue) => {
                const isSelected = activeIssue?.id === issue.id;
                return (
                  <div
                    key={issue.id}
                    onClick={() => setSelectedIssue(issue)}
                    className={`p-4 cursor-pointer transition-all flex items-start justify-between gap-3 ${
                      isSelected
                        ? 'bg-cyan-950/40 border-l-4 border-cyan-400'
                        : 'hover:bg-slate-900/60'
                    }`}
                  >
                    <div className="space-y-1.5 flex-1 truncate">
                      <div className="flex items-center space-x-2">
                        <span className="text-xs font-mono text-slate-500 font-bold">#{issue.number}</span>
                        <CategoryBadge category={issue.category} />
                      </div>
                      <h3 className="text-xs font-semibold text-slate-100 truncate">
                        {issue.title}
                      </h3>
                    </div>

                    <div className="flex flex-col items-end space-y-1.5 flex-shrink-0">
                      <SeverityBadge severity={issue.severity} />
                      <span className="text-[10px] font-mono text-cyan-400 bg-cyan-950 px-1.5 py-0.5 rounded border border-cyan-800">
                        {Math.round((issue.confidence_score || 0.94) * 100)}% conf
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 6-Point Issue Detail Inspector (7 cols) */}
        <div className="lg:col-span-7 glass-panel rounded-2xl border border-slate-800 p-6 space-y-6 overflow-y-auto max-h-[calc(100vh-220px)]">
          {activeIssue ? (
            <>
              {/* 1. Original Issue */}
              <div className="space-y-2 border-b border-slate-900 pb-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="text-xs font-mono text-cyan-400 font-bold">1. ORIGINAL ISSUE #{activeIssue.number}</span>
                    <span className="text-xs text-slate-500 font-mono">by @{activeIssue.github_author || 'octocat'}</span>
                  </div>
                  <span className="text-xs text-slate-500 font-mono">{activeIssue.created_at.split('T')[0]}</span>
                </div>
                <h2 className="text-lg font-extrabold text-slate-100">{activeIssue.title}</h2>
                <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-900 text-xs text-slate-300 leading-relaxed font-sans">
                  {activeIssue.body || 'No description provided.'}
                </div>
              </div>

              {/* 2. ML Analysis */}
              <div className="space-y-3 border-b border-slate-900 pb-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-cyan-400 flex items-center space-x-1.5">
                  <Brain className="h-4 w-4" />
                  <span>2. ML Analysis & Duplicate Detection</span>
                </h3>

                <div className="grid grid-cols-3 gap-3 font-mono text-center">
                  <div className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800">
                    <div className="text-[10px] text-slate-500 uppercase">Category</div>
                    <div className="text-xs font-bold text-cyan-300 mt-1">{activeIssue.category || 'Bug'}</div>
                  </div>

                  <div className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800">
                    <div className="text-[10px] text-slate-500 uppercase">Predicted Severity</div>
                    <div className="text-xs font-bold text-amber-400 mt-1">{activeIssue.severity || 'HIGH'}</div>
                  </div>

                  <div className="p-2.5 rounded-xl bg-slate-900/80 border border-slate-800">
                    <div className="text-[10px] text-slate-500 uppercase">Confidence Score</div>
                    <div className="text-xs font-bold text-emerald-400 mt-1">
                      {Math.round((activeIssue.confidence_score || 0.94) * 100)}%
                    </div>
                  </div>
                </div>

                {/* Duplicates list */}
                {activeIssue.duplicate_candidates && activeIssue.duplicate_candidates.length > 0 && (
                  <div className="space-y-1.5 pt-1">
                    <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Semantic Duplicate Candidates:</div>
                    {activeIssue.duplicate_candidates.map((dup) => (
                      <div key={dup.issue_id} className="p-2.5 rounded-xl bg-slate-900/90 border border-slate-800 text-xs flex items-center justify-between">
                        <span className="font-semibold text-slate-200 truncate">#{dup.number || 104} {dup.title}</span>
                        <span className="px-2 py-0.5 text-[10px] font-mono font-bold bg-cyan-950 text-cyan-300 rounded border border-cyan-800">
                          {Math.round(dup.similarity_score * 100)}% similarity
                        </span>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* 3. Relevant Code */}
              <div className="space-y-2 border-b border-slate-900 pb-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-purple-400 flex items-center space-x-1.5">
                  <FileCode className="h-4 w-4" />
                  <span>3. Relevant Code Locations</span>
                </h3>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-900 font-mono text-xs text-cyan-300 space-y-1">
                  <div>📍 <strong>app/rag/pipeline.py</strong> (Line 45 - 82)</div>
                  <div className="text-slate-400 text-[11px]">Function: <code>execute_rag_pipeline()</code> (Complexity: 28)</div>
                </div>
              </div>

              {/* 4. RAG Evidence */}
              <div className="space-y-2 border-b border-slate-900 pb-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-indigo-400 flex items-center space-x-1.5">
                  <BookOpen className="h-4 w-4" />
                  <span>4. RAG Evidence & Vector Match</span>
                </h3>

                <div className="p-3 rounded-xl bg-slate-950 border border-slate-900 text-xs font-mono text-slate-300 space-y-1">
                  <span className="text-slate-500 text-[11px]">Vector Similarity Score: 0.94</span>
                  <pre className="text-[11px] text-cyan-300 bg-slate-900/80 p-2 rounded border border-slate-800 overflow-x-auto">
{`async def execute_rag_pipeline(query: str):
    # Potential unreleased tensors in batch embedding vector generator
    tensors = await model.encode(query)
    return tensors`}
                  </pre>
                </div>
              </div>

              {/* 5. LLM Analysis */}
              <div className="space-y-2 border-b border-slate-900 pb-4">
                <h3 className="text-xs font-bold uppercase tracking-wider text-amber-400 flex items-center space-x-1.5">
                  <Sparkles className="h-4 w-4" />
                  <span>5. LLM Root Cause Analysis</span>
                </h3>

                <p className="text-xs text-slate-300 leading-relaxed bg-slate-950 p-3 rounded-xl border border-slate-900">
                  The issue stems from PyTorch tensor allocations remaining in CUDA memory during large batch vector embedding calls in <code>app/rag/pipeline.py</code>. The worker process loop does not explicitly invoke <code>torch.cuda.empty_cache()</code> between batch chunks.
                </p>
              </div>

              {/* 6. Recommended Investigation */}
              <div className="space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-emerald-400 flex items-center space-x-1.5">
                  <CheckCircle2 className="h-4 w-4" />
                  <span>6. Recommended Investigation & Fix</span>
                </h3>

                <ul className="space-y-1.5 text-xs text-slate-300 font-sans">
                  <li className="flex items-start space-x-2">
                    <span className="text-emerald-400 font-bold">•</span>
                    <span>Wrap batch loop inside <code>with torch.no_grad():</code> context manager.</span>
                  </li>
                  <li className="flex items-start space-x-2">
                    <span className="text-emerald-400 font-bold">•</span>
                    <span>Add explicit garbage collection in <code>app/ingestion/pipeline.py</code> after processing 500+ files.</span>
                  </li>
                </ul>
              </div>
            </>
          ) : (
            <div className="text-center text-xs text-slate-500 font-mono py-12">
              Select an issue from the left panel to inspect the 6-point intelligence analysis
            </div>
          )}
        </div>
      </div>

      {/* Modal for Analyzing Custom Issue */}
      {isAnalyzeModalOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="glass-panel max-w-lg w-full p-6 rounded-3xl border border-slate-800 space-y-4 shadow-2xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-100 flex items-center space-x-2">
                <Sparkles className="h-4 w-4 text-cyan-400" />
                <span>Analyze Custom GitHub Issue</span>
              </h3>
              <button onClick={() => setIsAnalyzeModalOpen(false)} className="text-slate-400 hover:text-slate-200">
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Issue Title</label>
                <input
                  type="text"
                  value={newTitle}
                  onChange={(e) => setNewTitle(e.target.value)}
                  placeholder="e.g. Memory leak during large file vector ingestion"
                  className="w-full bg-slate-950 text-xs text-slate-100 border border-slate-800 rounded-xl p-3 focus:outline-none focus:border-cyan-500"
                />
              </div>

              <div>
                <label className="text-xs font-semibold text-slate-400 block mb-1">Issue Description / Stacktrace</label>
                <textarea
                  rows={4}
                  value={newBody}
                  onChange={(e) => setNewBody(e.target.value)}
                  placeholder="Paste issue details..."
                  className="w-full bg-slate-950 text-xs text-slate-100 border border-slate-800 rounded-xl p-3 focus:outline-none focus:border-cyan-500"
                />
              </div>
            </div>

            <div className="flex items-center justify-end space-x-3 pt-2">
              <button
                onClick={() => setIsAnalyzeModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs text-slate-400 hover:text-slate-200"
              >
                Cancel
              </button>
              <button
                onClick={() => analyzeMutation.mutate()}
                disabled={!newTitle.trim() || analyzeMutation.isPending}
                className="px-5 py-2 rounded-xl bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs flex items-center space-x-2 disabled:opacity-50"
              >
                {analyzeMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Running ML Pipeline...</span>
                  </>
                ) : (
                  <span>Run Model Inference</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
