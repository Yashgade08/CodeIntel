/**
 * GitHubValidatePage - Complete CodeIntel Interface
 *
 * Capabilities:
 *   1. Validate & Clone GitHub repository
 *   2. Discover & scan files
 *   3. Index repository into ChromaDB vector database
 *   4. AI RAG Bug Detection with LLM analysis
 *   5. Interactive Source Code Viewer with highlighted evidence lines
 */

import React, { useState, useEffect } from 'react';
import { MermaidViewer } from '../components/MermaidViewer';

// ── Types ───────────────────────────────────────────────────────────────────

interface WorkspaceSummary {
  workspace_id: string;
  repository_name: string;
  frameworks: string[];
  created_at: number;
}

interface StructureGraphData {
  success: boolean;
  repository_name: string;
  frameworks: string[];
  top_modules: string[];
  mermaid_syntax: string;
}

interface FileItem {
  path: string;
  type: 'file' | 'directory';
  extension: string;
  size: number;
}

interface FilesScanSuccess {
  success: true;
  repository: {
    owner: string;
    name: string;
    workspace_id: string;
  };
  files: {
    total: number;
    directories: number;
    summary: Record<string, number>;
    items: FileItem[];
  };
}

interface IndexSuccess {
  success: true;
  repository_id: string;
  status: string;
  files_processed: number;
  chunks_created: number;
  embeddings_created: number;
}

interface BugFinding {
  title: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  confidence: number;
  category: string;
  file_path: string;
  start_line: number;
  end_line: number;
  description: string;
  root_cause: string;
  impact: string;
  suggested_fix: string;
  validation_status?: string;
  evidence: Array<{
    file_path: string;
    start_line: number;
    end_line: number;
  }>;
}

interface BugAnalysisSuccess {
  success: true;
  repository_id: string;
  query: string;
  summary: string;
  total_findings: number;
  findings: BugFinding[];
  retrieved_context_count: number;
}

interface SourceLine {
  line_number: number;
  content: string;
  is_highlighted: boolean;
}

interface SourceFileViewerData {
  file_path: string;
  total_lines: number;
  highlight_start: number;
  highlight_end: number;
  lines: SourceLine[];
}

interface ApiError {
  code: string;
  layer?: string;
  message: string;
  root_cause?: string;
  fix?: string;
}

export const GitHubValidatePage: React.FC = () => {
  const [url, setUrl] = useState('');
  const [activeWorkspaceId, setActiveWorkspaceId] = useState<string | null>(null);
  const [activeRepoName, setActiveRepoName] = useState<string | null>(null);

  // Status flags
  const [isCloning, setIsCloning] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [isIndexing, setIsIndexing] = useState(false);
  const [isAnalyzingBugs, setIsAnalyzingBugs] = useState(false);

  // Data states
  const [scannedData, setScannedData] = useState<FilesScanSuccess | null>(null);
  const [structureGraph, setStructureGraph] = useState<StructureGraphData | null>(null);
  const [isLoadingGraph, setIsLoadingGraph] = useState(false);
  const [indexData, setIndexData] = useState<IndexSuccess | null>(null);
  const [bugData, setBugData] = useState<BugAnalysisSuccess | null>(null);
  const [bugQuery, setBugQuery] = useState('Find potential bugs, logic errors, and security vulnerabilities');

  // Error state
  const [error, setError] = useState<ApiError | null>(null);

  // Source Viewer Modal State
  const [sourceViewer, setSourceViewer] = useState<SourceFileViewerData | null>(null);
  const [isLoadingSource, setIsLoadingSource] = useState(false);

  // Cloned repositories discovery
  const [existingWorkspaces, setExistingWorkspaces] = useState<WorkspaceSummary[]>([]);

  // Initial load: fetch existing cloned workspaces
  const refreshWorkspaces = async () => {
    try {
      const res = await fetch('/api/github/workspaces');
      const data = await res.json();
      if (data.success && data.workspaces) {
        setExistingWorkspaces(data.workspaces);
      }
    } catch (err: unknown) {
      console.error('Failed to load existing workspaces', err);
    }
  };

  useEffect(() => {
    refreshWorkspaces();
  }, []);

  // ── Fetch Structure Graph ──────────────────────────────────────────────────
  const fetchStructureGraph = async (wsId: string) => {
    setIsLoadingGraph(true);
    try {
      const res = await fetch(`/api/github/repositories/${encodeURIComponent(wsId)}/structure-graph`);
      const data = await res.json();
      if (data.success) {
        setStructureGraph(data);
      }
    } catch (err: unknown) {
      console.error('Failed to load structure graph', err);
    } finally {
      setIsLoadingGraph(false);
    }
  };

  // ── Load an Existing Workspace ────────────────────────────────────────────
  const loadWorkspace = async (wsId: string, repoName?: string) => {
    setError(null);
    setScannedData(null);
    setStructureGraph(null);
    setIndexData(null);
    setBugData(null);
    setActiveWorkspaceId(wsId);
    setActiveRepoName(repoName || wsId);

    setIsScanning(true);
    fetchStructureGraph(wsId);

    try {
      const scanRes = await fetch(`/api/github/repositories/${encodeURIComponent(wsId)}/files`);
      const scanJson = await scanRes.json();
      if (!scanJson.success) {
        setError(scanJson.error);
      } else {
        setScannedData(scanJson);
      }
    } catch (err: unknown) {
      console.error('Failed to load workspace files', err);
    } finally {
      setIsScanning(false);
    }
  };

  // ── 1. Clone & Scan ───────────────────────────────────────────────────────
  const handleCloneAndScan = async () => {
    const cleanUrl = url.trim();
    if (!cleanUrl) return;

    setError(null);
    setScannedData(null);
    setStructureGraph(null);
    setIndexData(null);
    setBugData(null);
    setIsCloning(true);

    try {
      const cloneRes = await fetch('/api/github/clone', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: cleanUrl }),
      });
      const cloneJson = await cloneRes.json();

      if (!cloneJson.success) {
        setError(cloneJson.error);
        setIsCloning(false);
        return;
      }

      const wsId = cloneJson.clone.workspace_id;
      const rName = `${cloneJson.repository.owner}/${cloneJson.repository.name}`;
      setActiveWorkspaceId(wsId);
      setActiveRepoName(rName);
      setIsCloning(false);

      // Now Scan & fetch Structure Graph
      setIsScanning(true);
      fetchStructureGraph(wsId);

      const scanRes = await fetch(`/api/github/repositories/${encodeURIComponent(wsId)}/files`);
      const scanJson = await scanRes.json();

      if (!scanJson.success) {
        setError(scanJson.error);
      } else {
        setScannedData(scanJson);
      }
    } catch (err: unknown) {
      setError({
        code: 'NETWORK_ERROR',
        layer: 'network',
        message: 'Failed to connect to backend server.',
        root_cause: err instanceof Error ? err.message : String(err),
        fix: 'Ensure FastAPI is running: uvicorn app.main:app --reload --port 8000',
      });
    } finally {
      setIsCloning(false);
      setIsScanning(false);
    }
  };

  // ── 2. Index Repository ───────────────────────────────────────────────────
  const handleIndex = async () => {
    if (!activeWorkspaceId) return;

    setError(null);
    setIsIndexing(true);

    try {
      const res = await fetch(`/api/github/repositories/${encodeURIComponent(activeWorkspaceId)}/index`, {
        method: 'POST',
      });
      const data = await res.json();

      if (!data.success) {
        setError(data.error);
      } else {
        setIndexData(data);
      }
    } catch (err: unknown) {
      setError({
        code: 'INDEXING_FAILED',
        layer: 'indexing',
        message: 'Failed to complete indexing.',
        root_cause: err instanceof Error ? err.message : String(err),
        fix: 'Check backend logs for details.',
      });
    } finally {
      setIsIndexing(false);
    }
  };

  // ── 3. Analyze Bugs ───────────────────────────────────────────────────────
  const handleAnalyzeBugs = async (customQuery?: string) => {
    if (!activeWorkspaceId) return;

    const queryToSend = customQuery || bugQuery;
    setError(null);
    setIsAnalyzingBugs(true);

    try {
      const res = await fetch(`/api/github/repositories/${encodeURIComponent(activeWorkspaceId)}/bugs/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: queryToSend }),
      });
      const data = await res.json();

      if (!data.success) {
        setError(data.error);
      } else {
        setBugData(data);
      }
    } catch (err: unknown) {
      setError({
        code: 'ANALYSIS_FAILED',
        layer: 'llm',
        message: 'Bug analysis failed.',
        root_cause: err instanceof Error ? err.message : String(err),
        fix: 'Check LLM API key and configuration.',
      });
    } finally {
      setIsAnalyzingBugs(false);
    }
  };

  // ── 4. Open Source Code Viewer ────────────────────────────────────────────
  const openSourceViewer = async (filePath: string, startLine: number, endLine: number) => {
    if (!activeWorkspaceId) return;

    setIsLoadingSource(true);
    try {
      const res = await fetch(
        `/api/github/repositories/${encodeURIComponent(activeWorkspaceId)}/file-content?path=${encodeURIComponent(
          filePath
        )}&start_line=${startLine}&end_line=${endLine}&context_lines=20`
      );
      const data = await res.json();

      if (data.success) {
        setSourceViewer(data);
      } else {
        setError(data.error);
      }
    } catch (err: unknown) {
      setError({
        code: 'VIEWER_ERROR',
        layer: 'source_viewer',
        message: 'Could not load source file content.',
        root_cause: err instanceof Error ? err.message : String(err),
      });
    } finally {
      setIsLoadingSource(false);
    }
  };

  const isBusy = isCloning || isScanning || isIndexing || isAnalyzingBugs || isLoadingSource;

  return (
    <div style={styles.page}>
      <div style={styles.container}>
        {/* Main Card */}
        <div style={styles.card}>
          <div style={styles.header}>
            <div style={styles.logoBadge}>⚡ CodeIntel • AI Code Review & Bug Detector</div>
            <h1 style={styles.title}>Repository Intelligence & Bug Analysis</h1>
            <p style={styles.subtitle}>
              Clone, chunk, embed into ChromaDB, and analyze repository defects with grounded RAG evidence
            </p>
          </div>

          {/* URL Input Form */}
          <div style={styles.form}>
            <input
              type="text"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://github.com/owner/repository"
              style={styles.input}
              disabled={isBusy}
            />

            <div style={styles.buttonGroup}>
              <button
                onClick={handleCloneAndScan}
                disabled={isBusy || !url.trim()}
                style={{
                  ...styles.button,
                  ...styles.primaryButton,
                  opacity: isBusy || !url.trim() ? 0.6 : 1,
                }}
              >
                {isCloning ? (
                  <span>🌀 Cloning Repository…</span>
                ) : isScanning ? (
                  <span>📁 Scanning Files…</span>
                ) : (
                  '🚀 Clone & Discover Files'
                )}
              </button>
            </div>
          </div>

          {/* Quick workspace switcher for already cloned repositories */}
          {existingWorkspaces.length > 0 && (
            <div style={styles.recentWorkspacesContainer}>
              <span style={styles.recentLabel}>⚡ Recent Workspaces:</span>
              <div style={styles.recentChips}>
                {existingWorkspaces.slice(0, 6).map((ws) => (
                  <button
                    key={ws.workspace_id}
                    onClick={() => loadWorkspace(ws.workspace_id, ws.repository_name)}
                    disabled={isBusy}
                    style={{
                      ...styles.recentChip,
                      borderColor: activeWorkspaceId === ws.workspace_id ? '#38bdf8' : '#334155',
                      backgroundColor: activeWorkspaceId === ws.workspace_id ? 'rgba(56, 189, 248, 0.15)' : '#090e1a',
                    }}
                    title={`Open workspace: ${ws.workspace_id}`}
                  >
                    <span style={{ color: activeWorkspaceId === ws.workspace_id ? '#38bdf8' : '#e2e8f0' }}>
                      {ws.repository_name}
                    </span>
                    {ws.frameworks && ws.frameworks.length > 0 && ws.frameworks[0] !== 'Generic Project' && (
                      <span style={styles.frameworkPill}>{ws.frameworks[0]}</span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Error Diagnostics Banner */}
          {error && (
            <div style={styles.errorBox}>
              <div style={styles.errorHeader}>
                <span style={styles.errorIcon}>⚠️</span>
                <span style={styles.errorTitle}>
                  [{error.layer?.toUpperCase() || 'ERROR'}] {error.message}
                </span>
              </div>
              {error.code && (
                <p style={styles.errorCode}>
                  <strong>Error Code:</strong> <code>{error.code}</code>
                </p>
              )}
              {error.root_cause && (
                <div style={styles.detailsBox}>
                  <strong>Root Cause:</strong>
                  <p style={styles.detailsText}>{error.root_cause}</p>
                </div>
              )}
              {error.fix && (
                <div style={styles.fixBox}>
                  <strong>💡 Suggested Fix:</strong>
                  <p style={styles.fixText}>{error.fix}</p>
                </div>
              )}
            </div>
          )}

          {/* Repository Cloned Section */}
          {activeWorkspaceId && (
            <div style={styles.repoSection}>
              <div style={styles.repoBanner}>
                <div>
                  <div style={styles.repoName}>
                    Repository: <strong style={{ color: '#38bdf8' }}>{activeRepoName || activeWorkspaceId}</strong>
                  </div>
                  <div style={styles.workspaceId}>
                    Workspace: <code>{activeWorkspaceId}</code>
                  </div>
                </div>

                <div style={styles.statusBadgeGreen}>🟢 Cloned</div>
              </div>

              {/* Step 2 Stats */}
              {scannedData && (
                <div style={styles.statsRow}>
                  <div style={styles.statBox}>
                    <span style={styles.statVal}>{scannedData.files.total}</span>
                    <span style={styles.statLbl}>Source Files</span>
                  </div>
                  <div style={styles.statBox}>
                    <span style={styles.statVal}>{scannedData.files.directories}</span>
                    <span style={styles.statLbl}>Directories</span>
                  </div>
                  <div style={styles.statBox}>
                    <span style={styles.statVal}>
                      {indexData ? 'Indexed' : 'Pending Index'}
                    </span>
                    <span style={styles.statLbl}>Vector Status</span>
                  </div>
                </div>
              )}

              {/* Architecture & Framework Structure Graph (Mermaid.js) */}
              {isLoadingGraph && (
                <div style={styles.graphLoadingBox}>
                  <div style={styles.miniSpinner}></div>
                  <span style={{ color: '#94a3b8', fontSize: '0.875rem' }}>
                    Mapping project architecture with Mermaid.js…
                  </span>
                </div>
              )}

              {structureGraph && (
                <MermaidViewer
                  syntax={structureGraph.mermaid_syntax}
                  frameworks={structureGraph.frameworks}
                  title={`📊 ${structureGraph.repository_name} Architecture & Structure`}
                />
              )}

              {/* Indexing Trigger */}
              <div style={styles.actionCard}>
                <div style={styles.actionInfo}>
                  <strong>Step 2: Vector Embedding & ChromaDB Indexing</strong>
                  <p style={styles.muted}>
                    Extract structure-aware code chunks and store deterministic embeddings in persistent ChromaDB.
                  </p>
                </div>

                <button
                  onClick={handleIndex}
                  disabled={isBusy}
                  style={{
                    ...styles.button,
                    ...styles.indexButton,
                    opacity: isBusy ? 0.6 : 1,
                  }}
                >
                  {isIndexing ? '⚡ Indexing Vectors…' : indexData ? '✓ Re-Index Vectors' : '⚡ Index Repository'}
                </button>
              </div>

              {/* Index Result Metrics */}
              {indexData && (
                <div style={styles.indexResultCard}>
                  <span style={styles.checkIcon}>✅</span>
                  <div>
                    <strong>ChromaDB Vectorstore Ready!</strong>
                    <div style={styles.indexStats}>
                      <span>📄 Files Processed: <strong>{indexData.files_processed}</strong></span>
                      <span>🧩 Chunks Created: <strong>{indexData.chunks_created}</strong></span>
                      <span>🔢 Embeddings Stored: <strong>{indexData.embeddings_created}</strong></span>
                    </div>
                  </div>
                </div>
              )}

              {/* Step 3: AI Bug Detection & Code Review */}
              {indexData && (
                <div style={styles.bugReviewSection}>
                  <div style={styles.sectionHeading}>
                    <h2>🔍 AI Code Review & Bug Detection</h2>
                    <p style={styles.muted}>
                      Ask targeted questions or analyze overall logic, security, and error-handling bugs.
                    </p>
                  </div>

                  <div style={styles.queryInputRow}>
                    <input
                      type="text"
                      value={bugQuery}
                      onChange={(e) => setBugQuery(e.target.value)}
                      placeholder="e.g. Find authentication bypasses or null pointer errors..."
                      style={styles.queryInput}
                      disabled={isBusy}
                    />
                    <button
                      onClick={() => handleAnalyzeBugs()}
                      disabled={isBusy || !bugQuery.trim()}
                      style={{
                        ...styles.button,
                        ...styles.analyzeButton,
                        opacity: isBusy || !bugQuery.trim() ? 0.6 : 1,
                      }}
                    >
                      {isAnalyzingBugs ? '🧠 Analyzing Code…' : '🐞 Find Bugs'}
                    </button>
                  </div>

                  {/* Preset Quick Query Tags */}
                  <div style={styles.presetTags}>
                    <span style={styles.presetLabel}>Quick queries:</span>
                    {[
                      'Find potential bugs and logic errors',
                      'Find authentication bugs',
                      'Find security & SQL injection vulnerabilities',
                      'Find division by zero and crash risks',
                      'Find error handling and unhandled exceptions',
                    ].map((preset) => (
                      <button
                        key={preset}
                        onClick={() => {
                          setBugQuery(preset);
                          handleAnalyzeBugs(preset);
                        }}
                        disabled={isBusy}
                        style={styles.presetBtn}
                      >
                        {preset}
                      </button>
                    ))}
                  </div>

                  {/* Bug Findings Display */}
                  {bugData && (
                    <div style={styles.findingsContainer}>
                      <div style={styles.findingsHeader}>
                        <div>
                          <h3 style={styles.findingsTitle}>
                            Review Findings ({bugData.total_findings})
                          </h3>
                          <p style={styles.summaryText}>{bugData.summary}</p>
                        </div>
                        <span style={styles.contextBadge}>
                          {bugData.retrieved_context_count} Context Chunks Analyzed
                        </span>
                      </div>

                      {bugData.findings.length === 0 ? (
                        <div style={styles.cleanReportBox}>
                          <span style={styles.cleanIcon}>🛡️</span>
                          <div>
                            <strong>No high-confidence bugs identified from analyzed evidence.</strong>
                            <p style={styles.cleanSubtext}>
                              The analyzed code context does not exhibit obvious verified logic or security defects.
                            </p>
                          </div>
                        </div>
                      ) : (
                        <div style={styles.cardsGrid}>
                          {bugData.findings.map((finding, idx) => (
                            <div key={idx} style={styles.bugCard}>
                              {/* Top row */}
                              <div style={styles.cardTopRow}>
                                <div style={styles.cardTitleWrap}>
                                  <span
                                    style={{
                                      ...styles.sevBadge,
                                      backgroundColor:
                                        finding.severity === 'HIGH'
                                          ? '#dc2626'
                                          : finding.severity === 'MEDIUM'
                                          ? '#d97706'
                                          : '#4b5563',
                                    }}
                                  >
                                    {finding.severity === 'HIGH'
                                      ? '🔴 HIGH'
                                      : finding.severity === 'MEDIUM'
                                      ? '🟠 MEDIUM'
                                      : '🟡 LOW'}
                                  </span>
                                  <h4 style={styles.findingTitle}>{finding.title}</h4>
                                </div>

                                <div style={styles.confPill}>
                                  Confidence: {Math.round(finding.confidence * 100)}%
                                </div>
                              </div>

                              {/* Evidence reference */}
                              <div style={styles.evidenceRow}>
                                <span style={styles.evidenceLabel}>File & Lines:</span>
                                <button
                                  onClick={() =>
                                    openSourceViewer(finding.file_path, finding.start_line, finding.end_line)
                                  }
                                  style={styles.evidenceLinkBtn}
                                >
                                  📄 {finding.file_path}:{finding.start_line}-{finding.end_line} ➔
                                </button>
                              </div>

                              {/* Why it is a problem */}
                              <div style={styles.fieldBlock}>
                                <strong style={styles.fieldHeading}>Why this is a problem:</strong>
                                <p style={styles.fieldContent}>{finding.description}</p>
                              </div>

                              {/* Root cause */}
                              <div style={styles.rootCauseBox}>
                                <strong>Root Cause:</strong>
                                <p style={styles.fieldContent}>{finding.root_cause}</p>
                              </div>

                              {/* Potential impact */}
                              <div style={styles.impactBox}>
                                <strong>Potential Impact:</strong>
                                <p style={styles.fieldContent}>{finding.impact}</p>
                              </div>

                              {/* Suggested fix */}
                              <div style={styles.fixSnippetBox}>
                                <strong>Suggested Fix:</strong>
                                <pre style={styles.fixCode}>{finding.suggested_fix}</pre>
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Interactive Source Code Viewer Modal */}
      {sourceViewer && (
        <div style={styles.modalOverlay} onClick={() => setSourceViewer(null)}>
          <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <div>
                <h3 style={styles.modalTitle}>📄 {sourceViewer.file_path}</h3>
                <p style={styles.modalSubtitle}>
                  Lines {sourceViewer.highlight_start} to {sourceViewer.highlight_end} flagged in bug finding
                </p>
              </div>
              <button onClick={() => setSourceViewer(null)} style={styles.closeBtn}>
                ✕ Close
              </button>
            </div>

            <div style={styles.modalBody}>
              <div style={styles.codeEditor}>
                {sourceViewer.lines.map((line) => (
                  <div
                    key={line.line_number}
                    style={{
                      ...styles.codeLineRow,
                      backgroundColor: line.is_highlighted ? 'rgba(239, 68, 68, 0.2)' : 'transparent',
                      borderLeft: line.is_highlighted ? '3px solid #ef4444' : '3px solid transparent',
                    }}
                  >
                    <span style={styles.lineNumber}>{line.line_number}</span>
                    <span style={styles.lineContent}>{line.content || ' '}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ── Styles ──────────────────────────────────────────────────────────────────

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    justifyContent: 'center',
    backgroundColor: '#070b14',
    backgroundImage: 'radial-gradient(ellipse 80% 80% at 50% -20%, rgba(56, 189, 248, 0.12), rgba(255, 255, 255, 0))',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    padding: '2rem 1rem',
    color: '#f1f5f9',
  },
  container: {
    width: '100%',
    maxWidth: '1024px',
  },
  card: {
    backgroundColor: '#0f172a',
    border: '1px solid #1e293b',
    borderRadius: '16px',
    padding: '2rem',
    boxShadow: '0 25px 60px -15px rgba(0, 0, 0, 0.7)',
  },
  header: {
    marginBottom: '1.5rem',
  },
  logoBadge: {
    display: 'inline-block',
    fontSize: '0.75rem',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    padding: '0.25rem 0.6rem',
    borderRadius: '9999px',
    backgroundColor: 'rgba(56, 189, 248, 0.12)',
    color: '#38bdf8',
    border: '1px solid rgba(56, 189, 248, 0.25)',
    marginBottom: '0.75rem',
  },
  title: {
    fontSize: '1.75rem',
    fontWeight: 800,
    letterSpacing: '-0.025em',
    margin: '0 0 0.4rem 0',
    color: '#ffffff',
  },
  subtitle: {
    color: '#94a3b8',
    fontSize: '0.92rem',
    margin: 0,
  },
  form: {
    display: 'flex',
    gap: '0.75rem',
    marginBottom: '1.5rem',
  },
  input: {
    flex: 1,
    padding: '0.85rem 1rem',
    borderRadius: '10px',
    border: '1px solid #334155',
    backgroundColor: '#090e1a',
    color: '#f8fafc',
    fontSize: '0.95rem',
    outline: 'none',
  },
  buttonGroup: {
    display: 'flex',
  },
  button: {
    padding: '0.85rem 1.25rem',
    borderRadius: '10px',
    fontSize: '0.92rem',
    fontWeight: 600,
    cursor: 'pointer',
    border: 'none',
    transition: 'all 0.2s',
  },
  primaryButton: {
    background: 'linear-gradient(135deg, #0ea5e9 0%, #6366f1 100%)',
    color: '#ffffff',
  },
  indexButton: {
    background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
    color: '#ffffff',
    whiteSpace: 'nowrap',
  },
  analyzeButton: {
    background: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
    color: '#ffffff',
    whiteSpace: 'nowrap',
    padding: '0.75rem 1.25rem',
  },
  errorBox: {
    backgroundColor: '#1f0d0d',
    border: '1px solid #991b1b',
    borderRadius: '12px',
    padding: '1.25rem',
    marginBottom: '1.5rem',
  },
  errorHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    marginBottom: '0.5rem',
  },
  errorIcon: {
    fontSize: '1.2rem',
  },
  errorTitle: {
    color: '#f87171',
    fontWeight: 700,
    fontSize: '0.98rem',
  },
  errorCode: {
    color: '#fca5a5',
    fontSize: '0.85rem',
    margin: '0.25rem 0 0.5rem 0',
  },
  detailsBox: {
    backgroundColor: '#150808',
    padding: '0.65rem 0.85rem',
    borderRadius: '8px',
    border: '1px solid #7f1d1d',
    color: '#fca5a5',
    fontSize: '0.82rem',
    marginBottom: '0.5rem',
  },
  detailsText: {
    margin: '0.25rem 0 0 0',
    fontFamily: 'monospace',
    fontSize: '0.8rem',
  },
  fixBox: {
    backgroundColor: '#1c1303',
    padding: '0.65rem 0.85rem',
    borderRadius: '8px',
    border: '1px solid #854d0e',
    color: '#fde047',
    fontSize: '0.82rem',
  },
  fixText: {
    margin: '0.25rem 0 0 0',
  },
  repoSection: {
    marginTop: '1.5rem',
    borderTop: '1px solid #1e293b',
    paddingTop: '1.5rem',
  },
  repoBanner: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1.25rem',
  },
  repoName: {
    fontSize: '1.2rem',
    color: '#cbd5e1',
  },
  workspaceId: {
    fontSize: '0.8rem',
    color: '#64748b',
    marginTop: '0.2rem',
  },
  statusBadgeGreen: {
    backgroundColor: '#04271d',
    border: '1px solid #059669',
    color: '#34d399',
    padding: '0.35rem 0.75rem',
    borderRadius: '9999px',
    fontSize: '0.82rem',
    fontWeight: 700,
  },
  statsRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: '1rem',
    marginBottom: '1.5rem',
  },
  statBox: {
    backgroundColor: '#090e1a',
    border: '1px solid #1e293b',
    borderRadius: '10px',
    padding: '1rem',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  statVal: {
    fontSize: '1.45rem',
    fontWeight: 800,
    color: '#f8fafc',
  },
  statLbl: {
    fontSize: '0.75rem',
    color: '#94a3b8',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    marginTop: '0.2rem',
  },
  actionCard: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#090e1a',
    border: '1px solid #1e293b',
    borderRadius: '12px',
    padding: '1.25rem',
    marginBottom: '1rem',
    gap: '1rem',
  },
  actionInfo: {
    flex: 1,
  },
  muted: {
    margin: '0.25rem 0 0 0',
    color: '#94a3b8',
    fontSize: '0.82rem',
  },
  indexResultCard: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
    backgroundColor: '#04271d',
    border: '1px solid #065f46',
    borderRadius: '10px',
    padding: '1rem',
    marginBottom: '1.5rem',
  },
  checkIcon: {
    fontSize: '1.5rem',
  },
  indexStats: {
    display: 'flex',
    gap: '1.25rem',
    fontSize: '0.85rem',
    color: '#a7f3d0',
    marginTop: '0.25rem',
  },
  bugReviewSection: {
    marginTop: '1.5rem',
    borderTop: '1px solid #1e293b',
    paddingTop: '1.5rem',
  },
  sectionHeading: {
    marginBottom: '1rem',
  },
  queryInputRow: {
    display: 'flex',
    gap: '0.75rem',
    marginBottom: '0.75rem',
  },
  queryInput: {
    flex: 1,
    padding: '0.75rem 1rem',
    borderRadius: '8px',
    border: '1px solid #334155',
    backgroundColor: '#090e1a',
    color: '#f8fafc',
    fontSize: '0.9rem',
    outline: 'none',
  },
  presetTags: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '0.5rem',
    alignItems: 'center',
    marginBottom: '1.5rem',
  },
  presetLabel: {
    fontSize: '0.75rem',
    color: '#64748b',
  },
  presetBtn: {
    fontSize: '0.75rem',
    backgroundColor: '#090e1a',
    border: '1px solid #1e293b',
    borderRadius: '6px',
    padding: '0.25rem 0.5rem',
    color: '#94a3b8',
    cursor: 'pointer',
  },
  findingsContainer: {
    marginTop: '1.5rem',
  },
  findingsHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '1.25rem',
    borderBottom: '1px solid #1e293b',
    paddingBottom: '0.75rem',
  },
  findingsTitle: {
    margin: '0 0 0.25rem 0',
    fontSize: '1.2rem',
    color: '#f8fafc',
  },
  summaryText: {
    margin: 0,
    color: '#94a3b8',
    fontSize: '0.85rem',
  },
  contextBadge: {
    fontSize: '0.75rem',
    backgroundColor: '#1e293b',
    color: '#93c5fd',
    padding: '0.2rem 0.5rem',
    borderRadius: '4px',
  },
  cleanReportBox: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
    padding: '1.5rem',
    backgroundColor: '#04271d',
    border: '1px solid #065f46',
    borderRadius: '12px',
  },
  cleanIcon: {
    fontSize: '2rem',
  },
  cleanSubtext: {
    margin: '0.25rem 0 0 0',
    color: '#a7f3d0',
    fontSize: '0.85rem',
  },
  cardsGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.25rem',
  },
  bugCard: {
    backgroundColor: '#090e1a',
    border: '1px solid #1e293b',
    borderRadius: '12px',
    padding: '1.25rem',
  },
  cardTopRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '0.75rem',
  },
  cardTitleWrap: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.6rem',
  },
  sevBadge: {
    fontSize: '0.72rem',
    fontWeight: 700,
    color: '#ffffff',
    padding: '0.2rem 0.5rem',
    borderRadius: '4px',
  },
  findingTitle: {
    margin: 0,
    fontSize: '1.05rem',
    color: '#f8fafc',
  },
  confPill: {
    fontSize: '0.75rem',
    color: '#60a5fa',
    backgroundColor: '#172554',
    padding: '0.2rem 0.5rem',
    borderRadius: '4px',
    border: '1px solid #1e40af',
  },
  evidenceRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    fontSize: '0.85rem',
    marginBottom: '0.75rem',
  },
  evidenceLabel: {
    color: '#94a3b8',
    fontWeight: 600,
  },
  evidenceLinkBtn: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    color: '#38bdf8',
    borderRadius: '6px',
    padding: '0.2rem 0.5rem',
    fontSize: '0.8rem',
    fontFamily: 'monospace',
    cursor: 'pointer',
  },
  fieldBlock: {
    fontSize: '0.85rem',
    marginBottom: '0.75rem',
  },
  fieldHeading: {
    color: '#cbd5e1',
  },
  fieldContent: {
    margin: '0.25rem 0 0 0',
    color: '#94a3b8',
  },
  rootCauseBox: {
    backgroundColor: '#150808',
    border: '1px solid #450a0a',
    borderRadius: '8px',
    padding: '0.75rem',
    fontSize: '0.82rem',
    color: '#fca5a5',
    marginBottom: '0.5rem',
  },
  impactBox: {
    backgroundColor: '#1c1303',
    border: '1px solid #78350f',
    borderRadius: '8px',
    padding: '0.75rem',
    fontSize: '0.82rem',
    color: '#fde047',
    marginBottom: '0.75rem',
  },
  fixSnippetBox: {
    backgroundColor: '#041f18',
    border: '1px solid #065f46',
    borderRadius: '8px',
    padding: '0.75rem',
    fontSize: '0.82rem',
  },
  fixCode: {
    margin: '0.4rem 0 0 0',
    fontFamily: 'monospace',
    fontSize: '0.78rem',
    color: '#6ee7b7',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-all',
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.8)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
    padding: '1.5rem',
  },
  modalContent: {
    backgroundColor: '#090e1a',
    border: '1px solid #334155',
    borderRadius: '14px',
    width: '100%',
    maxWidth: '800px',
    maxHeight: '85vh',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 25px 60px rgba(0,0,0,0.9)',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '1.25rem 1.5rem',
    borderBottom: '1px solid #1e293b',
  },
  modalTitle: {
    margin: 0,
    fontSize: '1.1rem',
    color: '#ffffff',
  },
  modalSubtitle: {
    margin: '0.2rem 0 0 0',
    color: '#94a3b8',
    fontSize: '0.8rem',
  },
  closeBtn: {
    backgroundColor: '#1e293b',
    border: 'none',
    color: '#cbd5e1',
    padding: '0.4rem 0.75rem',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '0.85rem',
  },
  modalBody: {
    padding: '1rem',
    overflowY: 'auto',
    flex: 1,
  },
  codeEditor: {
    fontFamily: 'monospace',
    fontSize: '0.85rem',
    backgroundColor: '#020617',
    borderRadius: '8px',
    padding: '0.5rem 0',
    border: '1px solid #1e293b',
  },
  codeLineRow: {
    display: 'flex',
    padding: '0.15rem 0.75rem',
  },
  lineNumber: {
    width: '45px',
    color: '#475569',
    textAlign: 'right',
    marginRight: '1rem',
    userSelect: 'none',
    flexShrink: 0,
  },
  lineContent: {
    color: '#e2e8f0',
    whiteSpace: 'pre',
    overflowX: 'auto',
  },
  recentWorkspacesContainer: {
    marginBottom: '1.25rem',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.4rem',
  },
  recentLabel: {
    fontSize: '0.75rem',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
    color: '#64748b',
  },
  recentChips: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '0.5rem',
  },
  recentChip: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.4rem',
    padding: '0.35rem 0.75rem',
    borderRadius: '8px',
    border: '1px solid #334155',
    backgroundColor: '#090e1a',
    color: '#e2e8f0',
    fontSize: '0.8rem',
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  frameworkPill: {
    fontSize: '0.68rem',
    fontWeight: 700,
    padding: '0.1rem 0.35rem',
    borderRadius: '4px',
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
    color: '#38bdf8',
    border: '1px solid rgba(56, 189, 248, 0.3)',
  },
  graphLoadingBox: {
    marginTop: '1.25rem',
    padding: '1.25rem',
    backgroundColor: '#090e1a',
    border: '1px dashed #334155',
    borderRadius: '12px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '0.75rem',
  },
  miniSpinner: {
    width: '18px',
    height: '18px',
    border: '2px solid rgba(56, 189, 248, 0.2)',
    borderTop: '2px solid #38bdf8',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
};
