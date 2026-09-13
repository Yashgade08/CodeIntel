/**
 * GitHubValidatePage - Complete CodeIntel Interface
 *
 * Capabilities:
 *   1. Validate & Clone GitHub repository
 *   2. Discover & scan files
 *   3. Index repository into ChromaDB vector database
 *   4. AI RAG Bug Detection with LLM analysis
 *   5. Interactive Source Code Viewer with highlighted evidence lines
 *   6. Architecture & AST Structure Mermaid diagrams
 */

import React, { useState, useEffect, useCallback } from 'react';
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

interface FileStructureMetrics {
  classes: number;
  methods: number;
  functions: number;
  imports: number;
  internal_calls: number;
}

interface FileStructureResponse {
  success: boolean;
  repository_id: string;
  file_path: string;
  language: string;
  total_lines: number;
  metrics: FileStructureMetrics;
  mermaid_syntax: string;
  class_diagram_syntax?: string;
  active_syntax?: string;
  format?: string;
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

  // Backend connection status
  const [isBackendOnline, setIsBackendOnline] = useState<boolean | null>(null);

  // Data states
  const [scannedData, setScannedData] = useState<FilesScanSuccess | null>(null);
  const [structureGraph, setStructureGraph] = useState<StructureGraphData | null>(null);
  const [isLoadingGraph, setIsLoadingGraph] = useState(false);
  const [indexData, setIndexData] = useState<IndexSuccess | null>(null);
  const [bugData, setBugData] = useState<BugAnalysisSuccess | null>(null);
  const [bugQuery, setBugQuery] = useState('Find potential bugs, logic errors, and security vulnerabilities');

  // Error state
  const [error, setError] = useState<ApiError | null>(null);

  // Source Viewer & File Structure Modal State
  const [sourceViewer, setSourceViewer] = useState<SourceFileViewerData | null>(null);
  const [isLoadingSource, setIsLoadingSource] = useState(false);
  const [modalActiveTab, setModalActiveTab] = useState<'code' | 'structure'>('code');
  const [fileStructureData, setFileStructureData] = useState<FileStructureResponse | null>(null);
  const [isLoadingFileStructure, setIsLoadingFileStructure] = useState(false);

  // File Architecture Explorer Filter State
  const [fileFilterQuery, setFileFilterQuery] = useState('');
  const [selectedLanguageFilter, setSelectedLanguageFilter] = useState<string>('all');

  // Cloned repositories discovery
  const [existingWorkspaces, setExistingWorkspaces] = useState<WorkspaceSummary[]>([]);

  // Backend Health Checker
  const checkBackendHealth = useCallback(async () => {
    try {
      const res = await fetch('/api/health');
      const data = await res.json();
      setIsBackendOnline(data.status === 'ok');
    } catch {
      setIsBackendOnline(false);
    }
  }, []);

  // Initial load: fetch existing cloned workspaces & check health
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
    checkBackendHealth();
    refreshWorkspaces();
    const interval = setInterval(checkBackendHealth, 12000);
    return () => clearInterval(interval);
  }, [checkBackendHealth]);

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

      // Refresh workspace list
      refreshWorkspaces();

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

  // ── Fetch File Internal Structure (Mermaid) ──────────────────────────────
  const fetchFileStructure = async (filePath: string, format = 'flowchart') => {
    if (!activeWorkspaceId) return;
    setIsLoadingFileStructure(true);
    try {
      const res = await fetch(
        `/api/github/repositories/${encodeURIComponent(activeWorkspaceId)}/file-structure?path=${encodeURIComponent(
          filePath
        )}&format=${format}`
      );
      const data = await res.json();
      if (data.success) {
        setFileStructureData(data);
      }
    } catch (err: unknown) {
      console.error('Failed to fetch file structure', err);
    } finally {
      setIsLoadingFileStructure(false);
    }
  };

  // ── 4. Open Source Code Viewer ────────────────────────────────────────────
  const openSourceViewer = async (filePath: string, startLine: number, endLine: number) => {
    if (!activeWorkspaceId) return;

    setModalActiveTab('code');
    setIsLoadingSource(true);
    fetchFileStructure(filePath);

    try {
      const res = await fetch(
        `/api/github/repositories/${encodeURIComponent(activeWorkspaceId)}/file-content?path=${encodeURIComponent(
          filePath
        )}&start_line=${startLine}&end_line=${endLine}&context_lines=25`
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

  // ── 5. Open Modal Directly into Structure Mode ────────────────────────────
  const openFileStructureViewer = async (filePath: string) => {
    if (!activeWorkspaceId) return;

    setModalActiveTab('structure');
    setIsLoadingFileStructure(true);
    setSourceViewer({
      file_path: filePath,
      total_lines: 0,
      highlight_start: 1,
      highlight_end: 1,
      lines: [],
    });

    fetchFileStructure(filePath);
    try {
      const res = await fetch(
        `/api/github/repositories/${encodeURIComponent(activeWorkspaceId)}/file-content?path=${encodeURIComponent(
          filePath
        )}&start_line=1&end_line=30&context_lines=30`
      );
      const data = await res.json();
      if (data.success) {
        setSourceViewer(data);
      }
    } catch {
      // Non-blocking
    }
  };

  // Filtered files for File Architecture Explorer
  const allFiles = scannedData?.files?.items || [];
  const availableLanguages = [
    'all',
    ...Array.from(
      new Set(
        allFiles
          .map((f) => f.extension.replace('.', '').toLowerCase())
          .filter((ext) => Boolean(ext))
      )
    ).slice(0, 8),
  ];

  const filteredFiles = allFiles.filter((file) => {
    const matchesSearch =
      !fileFilterQuery ||
      file.path.toLowerCase().includes(fileFilterQuery.toLowerCase()) ||
      file.extension.toLowerCase().includes(fileFilterQuery.toLowerCase());

    const matchesLang =
      selectedLanguageFilter === 'all' ||
      file.extension.replace('.', '').toLowerCase() === selectedLanguageFilter.toLowerCase();

    return matchesSearch && matchesLang;
  });

  const isBusy = isCloning || isScanning || isIndexing || isAnalyzingBugs || isLoadingSource;

  return (
    <div style={styles.page}>
      {/* Top Brand & Status Navigation Bar */}
      <header style={styles.topNavbar}>
        <div style={styles.navInner}>
          <div style={styles.navBrand}>
            <div style={styles.navLogoWrap}>
              <span style={styles.navLogoIcon}>⚡</span>
              <span style={styles.navLogoTitle}>CodeIntel</span>
              <span style={styles.navVersionBadge}>v0.1.0</span>
            </div>
            <span style={styles.navDivider}>/</span>
            <span style={styles.navTagline}>AI Code Review &amp; Bug Intelligence</span>
          </div>

          <div style={styles.navActions}>
            {/* Real-time Backend Health Indicator */}
            <div
              style={{
                ...styles.backendStatusPill,
                backgroundColor:
                  isBackendOnline === true
                    ? 'rgba(16, 185, 129, 0.15)'
                    : isBackendOnline === false
                    ? 'rgba(239, 68, 68, 0.15)'
                    : 'rgba(245, 158, 11, 0.15)',
                borderColor:
                  isBackendOnline === true
                    ? 'rgba(16, 185, 129, 0.4)'
                    : isBackendOnline === false
                    ? 'rgba(239, 68, 68, 0.4)'
                    : 'rgba(245, 158, 11, 0.4)',
              }}
              title={
                isBackendOnline === true
                  ? 'FastAPI Backend running on 127.0.0.1:8000'
                  : 'FastAPI Backend not responding'
              }
            >
              <span
                style={{
                  ...styles.statusDot,
                  backgroundColor:
                    isBackendOnline === true
                      ? '#10b981'
                      : isBackendOnline === false
                      ? '#ef4444'
                      : '#f59e0b',
                }}
              />
              <span
                style={{
                  ...styles.statusText,
                  color:
                    isBackendOnline === true
                      ? '#6ee7b7'
                      : isBackendOnline === false
                      ? '#fca5a5'
                      : '#fcd34d',
                }}
              >
                {isBackendOnline === true
                  ? 'FastAPI Online (8000)'
                  : isBackendOnline === false
                  ? 'FastAPI Offline'
                  : 'Checking Backend…'}
              </span>
            </div>

            <a
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noreferrer"
              style={styles.navLink}
              title="Open FastAPI Swagger API Docs"
            >
              📖 API Docs
            </a>
          </div>
        </div>
      </header>

      {/* Main Content Area */}
      <main style={styles.container}>
        {/* Main Card */}
        <div style={styles.card}>
          <div style={styles.header}>
            <div style={styles.logoBadge}>
              <span style={{ color: '#38bdf8', marginRight: '0.35rem' }}>⚡</span>
              CODEINTEL PLATFORM • GROUNDED RAG CODE INTELLIGENCE
            </div>
            <h1 style={styles.title}>Repository Intelligence &amp; Defect Analysis</h1>
            <p style={styles.subtitle}>
              Clone, chunk, embed into ChromaDB vectorstore, and analyze repository defects with verified AST &amp; RAG evidence.
            </p>
          </div>

          {/* URL Input Form */}
          <div style={styles.form}>
            <div style={styles.inputWrapper}>
              <span style={styles.inputIcon}>🔗</span>
              <input
                type="text"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="Enter GitHub URL (e.g. https://github.com/owner/repository)..."
                style={styles.input}
                disabled={isBusy}
              />
            </div>

            <div style={styles.buttonGroup}>
              <button
                onClick={handleCloneAndScan}
                disabled={isBusy || !url.trim()}
                style={{
                  ...styles.button,
                  ...styles.primaryButton,
                  opacity: isBusy || !url.trim() ? 0.65 : 1,
                  cursor: isBusy || !url.trim() ? 'not-allowed' : 'pointer',
                }}
              >
                {isCloning ? (
                  <span style={styles.btnContent}>
                    <span style={styles.btnSpinner} />
                    <span>Cloning Repository…</span>
                  </span>
                ) : isScanning ? (
                  <span style={styles.btnContent}>
                    <span style={styles.btnSpinner} />
                    <span>Scanning Files…</span>
                  </span>
                ) : (
                  <span style={styles.btnContent}>
                    <span>🔬</span>
                    <span>Clone &amp; Discover Files</span>
                  </span>
                )}
              </button>
            </div>
          </div>

          {/* Quick workspace switcher for already cloned repositories */}
          {existingWorkspaces.length > 0 && (
            <div style={styles.recentWorkspacesContainer}>
              <div style={styles.recentHeaderRow}>
                <span style={styles.recentLabel}>⚡ RECENT WORKSPACES</span>
                <span style={styles.recentHint}>Click to reload without recloning</span>
              </div>
              <div style={styles.recentChips}>
                {existingWorkspaces.slice(0, 8).map((ws) => (
                  <button
                    key={ws.workspace_id}
                    onClick={() => loadWorkspace(ws.workspace_id, ws.repository_name)}
                    disabled={isBusy}
                    style={{
                      ...styles.recentChip,
                      borderColor: activeWorkspaceId === ws.workspace_id ? '#38bdf8' : 'rgba(255, 255, 255, 0.15)',
                      backgroundColor:
                        activeWorkspaceId === ws.workspace_id ? 'rgba(56, 189, 248, 0.18)' : '#111c34',
                      boxShadow:
                        activeWorkspaceId === ws.workspace_id ? '0 0 16px rgba(56, 189, 248, 0.25)' : 'none',
                    }}
                    title={`Open workspace: ${ws.workspace_id}`}
                  >
                    <span
                      style={{
                        color: activeWorkspaceId === ws.workspace_id ? '#38bdf8' : '#f1f5f9',
                        fontWeight: activeWorkspaceId === ws.workspace_id ? 700 : 500,
                      }}
                    >
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

          {/* Error Diagnostics Banner (High-Contrast Redesign) */}
          {error && (
            <div style={styles.errorBox}>
              <div style={styles.errorHeader}>
                <span style={styles.errorIcon}>⚠️</span>
                <span style={styles.errorTitle}>
                  [{error.layer?.toUpperCase() || 'ERROR'}] {error.message}
                </span>
              </div>
              {error.code && (
                <div style={styles.errorCodeRow}>
                  <span style={styles.errorCodeLabel}>Error Code:</span>
                  <code style={styles.errorCodeBadge}>{error.code}</code>
                </div>
              )}
              {error.root_cause && (
                <div style={styles.detailsBox}>
                  <span style={styles.detailsHeading}>🔍 Root Cause:</span>
                  <p style={styles.detailsText}>{error.root_cause}</p>
                </div>
              )}
              {error.fix && (
                <div style={styles.fixBox}>
                  <span style={styles.fixHeading}>💡 Suggested Fix:</span>
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
                    Repository: <strong style={{ color: '#38bdf8', fontWeight: 700 }}>{activeRepoName || activeWorkspaceId}</strong>
                  </div>
                  <div style={styles.workspaceId}>
                    Workspace ID: <code style={styles.wsIdCode}>{activeWorkspaceId}</code>
                  </div>
                </div>

                <div style={styles.statusBadgeGreen}>
                  <span style={styles.pulsingDot} />
                  <span>Cloned &amp; Ready</span>
                </div>
              </div>

              {/* Step 2 Stats */}
              {scannedData && (
                <div style={styles.statsRow}>
                  <div style={styles.statBox}>
                    <span style={{ ...styles.statVal, color: '#38bdf8' }}>{scannedData.files.total}</span>
                    <span style={styles.statLbl}>Source Files</span>
                  </div>
                  <div style={styles.statBox}>
                    <span style={{ ...styles.statVal, color: '#818cf8' }}>{scannedData.files.directories}</span>
                    <span style={styles.statLbl}>Directories</span>
                  </div>
                  <div style={styles.statBox}>
                    <span style={{ ...styles.statVal, color: indexData ? '#34d399' : '#fbbf24' }}>
                      {indexData ? 'Indexed ✓' : 'Pending Index'}
                    </span>
                    <span style={styles.statLbl}>Vector Status</span>
                  </div>
                </div>
              )}

              {/* Architecture & Framework Structure Graph (Mermaid.js) */}
              {isLoadingGraph && (
                <div style={styles.graphLoadingBox}>
                  <div style={styles.miniSpinner} />
                  <span style={{ color: '#cbd5e1', fontSize: '0.9rem', fontWeight: 500 }}>
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

              {/* File Architecture & Internal Structure Explorer */}
              {scannedData && scannedData.files && scannedData.files.items && (
                <div style={styles.fileExplorerCard}>
                  <div style={styles.fileExplorerHeader}>
                    <div>
                      <h3 style={styles.explorerTitle}>📁 File Architecture &amp; AST Structure Explorer</h3>
                      <p style={styles.muted}>
                        Click any file to inspect its internal AST classes, methods, functions, and Mermaid diagram.
                      </p>
                    </div>
                    <span style={styles.fileCountPill}>
                      {filteredFiles.length} of {scannedData.files.items.length} Files
                    </span>
                  </div>

                  {/* Search and Language Filters */}
                  <div style={styles.fileExplorerFilterRow}>
                    <div style={styles.fileSearchWrapper}>
                      <span style={styles.fileSearchIcon}>🔍</span>
                      <input
                        type="text"
                        value={fileFilterQuery}
                        onChange={(e) => setFileFilterQuery(e.target.value)}
                        placeholder="Search files by path or extension (e.g. main.py, chunker, .tsx)..."
                        style={styles.fileSearchInput}
                      />
                    </div>
                    <div style={styles.langFilterChips}>
                      {availableLanguages.map((lang) => (
                        <button
                          key={lang}
                          onClick={() => setSelectedLanguageFilter(lang)}
                          style={{
                            ...styles.langChip,
                            backgroundColor: selectedLanguageFilter === lang ? '#0284c7' : '#111c34',
                            color: selectedLanguageFilter === lang ? '#ffffff' : '#cbd5e1',
                            border: selectedLanguageFilter === lang ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.12)',
                            boxShadow: selectedLanguageFilter === lang ? '0 0 12px rgba(2, 132, 199, 0.35)' : 'none',
                          }}
                        >
                          {lang.toUpperCase()}
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* File List Items */}
                  <div style={styles.fileItemsContainer}>
                    {filteredFiles.slice(0, 40).map((file) => (
                      <div key={file.path} style={styles.fileItemRow}>
                        <div style={styles.fileItemInfo}>
                          <span style={styles.fileIcon}>📄</span>
                          <span style={styles.filePathText} title={file.path}>
                            {file.path}
                          </span>
                          <span style={styles.fileExtBadge}>{file.extension || 'file'}</span>
                          <span style={styles.fileSizeText}>{(file.size / 1024).toFixed(1)} KB</span>
                        </div>
                        <div style={styles.fileItemActions}>
                          <button
                            onClick={() => openFileStructureViewer(file.path)}
                            style={styles.viewStructureBtn}
                            title="Generate and view Mermaid internal structure diagram"
                          >
                            📊 Structure
                          </button>
                          <button
                            onClick={() => openSourceViewer(file.path, 1, 40)}
                            style={styles.viewCodeBtn}
                            title="View source code"
                          >
                            💻 Code
                          </button>
                        </div>
                      </div>
                    ))}
                    {filteredFiles.length > 40 && (
                      <div style={styles.moreFilesNotice}>
                        Showing first 40 of {filteredFiles.length} matching files. Use the search input above to narrow down results.
                      </div>
                    )}
                    {filteredFiles.length === 0 && (
                      <div style={styles.moreFilesNotice}>
                        No source files matched your search filter.
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* Indexing Trigger */}
              <div style={styles.actionCard}>
                <div style={styles.actionInfo}>
                  <div style={styles.actionBadge}>STEP 2</div>
                  <h3 style={styles.actionHeading}>Vector Embedding &amp; ChromaDB Indexing</h3>
                  <p style={styles.actionDesc}>
                    Extract AST-aware code chunks and store high-dimensional embeddings in ChromaDB vectorstore for grounded AI queries.
                  </p>
                </div>

                <button
                  onClick={handleIndex}
                  disabled={isBusy}
                  style={{
                    ...styles.button,
                    ...styles.indexButton,
                    opacity: isBusy ? 0.65 : 1,
                    cursor: isBusy ? 'not-allowed' : 'pointer',
                  }}
                >
                  {isIndexing ? (
                    <span style={styles.btnContent}>
                      <span style={styles.btnSpinner} />
                      <span>Indexing Vectors…</span>
                    </span>
                  ) : indexData ? (
                    <span style={styles.btnContent}>
                      <span>✓</span>
                      <span>Re-Index Vectors</span>
                    </span>
                  ) : (
                    <span style={styles.btnContent}>
                      <span>⚡</span>
                      <span>Index Repository</span>
                    </span>
                  )}
                </button>
              </div>

              {/* Index Result Metrics */}
              {indexData && (
                <div style={styles.indexResultCard}>
                  <span style={styles.checkIcon}>✅</span>
                  <div>
                    <h4 style={styles.indexResultHeading}>ChromaDB Vectorstore Ready</h4>
                    <div style={styles.indexStats}>
                      <span style={styles.indexStatItem}>📄 Files Processed: <strong>{indexData.files_processed}</strong></span>
                      <span style={styles.indexStatItem}>🧩 Chunks Created: <strong>{indexData.chunks_created}</strong></span>
                      <span style={styles.indexStatItem}>🔢 Embeddings Stored: <strong>{indexData.embeddings_created}</strong></span>
                    </div>
                  </div>
                </div>
              )}

              {/* Step 3: AI Bug Detection & Code Review */}
              {indexData && (
                <div style={styles.bugReviewSection}>
                  <div style={styles.sectionHeading}>
                    <div style={{ ...styles.actionBadge, backgroundColor: 'rgba(239, 68, 68, 0.2)', color: '#f87171' }}>
                      STEP 3 • AI ANALYSIS
                    </div>
                    <h2 style={styles.sectionTitle}>🔍 AI Code Review &amp; Bug Detection</h2>
                    <p style={styles.sectionSubtitle}>
                      Perform grounded RAG code review using retrieved context vectors, detecting logic bugs, memory leaks, and security flaws.
                    </p>
                  </div>

                  <div style={styles.queryInputRow}>
                    <input
                      type="text"
                      value={bugQuery}
                      onChange={(e) => setBugQuery(e.target.value)}
                      placeholder="e.g. Find authentication bypasses, race conditions, or unhandled exceptions..."
                      style={styles.queryInput}
                      disabled={isBusy}
                    />
                    <button
                      onClick={() => handleAnalyzeBugs()}
                      disabled={isBusy || !bugQuery.trim()}
                      style={{
                        ...styles.button,
                        ...styles.analyzeButton,
                        opacity: isBusy || !bugQuery.trim() ? 0.65 : 1,
                        cursor: isBusy || !bugQuery.trim() ? 'not-allowed' : 'pointer',
                      }}
                    >
                      {isAnalyzingBugs ? (
                        <span style={styles.btnContent}>
                          <span style={styles.btnSpinner} />
                          <span>Analyzing Code…</span>
                        </span>
                      ) : (
                        <span style={styles.btnContent}>
                          <span>🐞</span>
                          <span>Find Bugs</span>
                        </span>
                      )}
                    </button>
                  </div>

                  {/* Preset Quick Query Tags */}
                  <div style={styles.presetTags}>
                    <span style={styles.presetLabel}>QUICK PROMPTS:</span>
                    {[
                      'Find potential bugs and logic errors',
                      'Find authentication & permission bugs',
                      'Find security & injection vulnerabilities',
                      'Find unhandled exceptions and crash risks',
                      'Find memory & resource leaks',
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
                          {bugData.retrieved_context_count} Context Vectors Analyzed
                        </span>
                      </div>

                      {bugData.findings.length === 0 ? (
                        <div style={styles.cleanReportBox}>
                          <span style={styles.cleanIcon}>🛡️</span>
                          <div>
                            <strong style={{ color: '#ffffff', fontSize: '1rem' }}>
                              No high-confidence bugs identified from analyzed evidence.
                            </strong>
                            <p style={styles.cleanSubtext}>
                              The analyzed repository context does not exhibit verified logic defects or security flaws for this query.
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
                                          : '#0284c7',
                                    }}
                                  >
                                    {finding.severity === 'HIGH'
                                      ? '🔴 HIGH'
                                      : finding.severity === 'MEDIUM'
                                      ? '🟠 MEDIUM'
                                      : '🔵 LOW'}
                                  </span>
                                  <h4 style={styles.findingTitle}>{finding.title}</h4>
                                </div>

                                <div style={styles.confPill}>
                                  Confidence: {Math.round(finding.confidence * 100)}%
                                </div>
                              </div>

                              {/* Evidence reference */}
                              <div style={styles.evidenceRow}>
                                <span style={styles.evidenceLabel}>Flagged Code:</span>
                                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                  <button
                                    onClick={() =>
                                      openSourceViewer(finding.file_path, finding.start_line, finding.end_line)
                                    }
                                    style={styles.evidenceLinkBtn}
                                    title="Open code viewer with highlighted bug lines"
                                  >
                                    📄 {finding.file_path}:{finding.start_line}-{finding.end_line} ➔
                                  </button>
                                  <button
                                    onClick={() => openFileStructureViewer(finding.file_path)}
                                    style={styles.evidenceStructureBtn}
                                    title="View Mermaid internal architecture diagram of this file"
                                  >
                                    📊 AST Structure
                                  </button>
                                </div>
                              </div>

                              {/* Why it is a problem */}
                              <div style={styles.fieldBlock}>
                                <strong style={styles.fieldHeading}>Description:</strong>
                                <p style={styles.fieldContent}>{finding.description}</p>
                              </div>

                              {/* Root cause */}
                              <div style={styles.rootCauseBox}>
                                <strong style={styles.rootCauseHeading}>🔍 Root Cause:</strong>
                                <p style={styles.fieldContent}>{finding.root_cause}</p>
                              </div>

                              {/* Potential impact */}
                              <div style={styles.impactBox}>
                                <strong style={styles.impactHeading}>💥 Impact:</strong>
                                <p style={styles.fieldContent}>{finding.impact}</p>
                              </div>

                              {/* Suggested fix */}
                              <div style={styles.fixSnippetBox}>
                                <strong style={styles.fixSnippetHeading}>💡 Suggested Resolution:</strong>
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
      </main>

      {/* Interactive Source Code & File Structure Viewer Modal */}
      {sourceViewer && (
        <div style={styles.modalOverlay} onClick={() => setSourceViewer(null)}>
          <div style={styles.modalContent} onClick={(e) => e.stopPropagation()}>
            <div style={styles.modalHeader}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', marginBottom: '0.35rem' }}>
                  <h3 style={styles.modalTitle}>📄 {sourceViewer.file_path}</h3>
                  {fileStructureData && (
                    <span style={styles.modalLangBadge}>
                      {fileStructureData.language.toUpperCase()}
                    </span>
                  )}
                </div>
                <p style={styles.modalSubtitle}>
                  {modalActiveTab === 'code'
                    ? sourceViewer.highlight_start && sourceViewer.highlight_end
                      ? `Lines ${sourceViewer.highlight_start} to ${sourceViewer.highlight_end} highlighted from bug evidence`
                      : 'Source code preview'
                    : 'Internal AST architecture, classes, methods, functions, and call flow'}
                </p>
              </div>

              {/* Mode Switch Tabs */}
              <div style={styles.modalTabs}>
                <button
                  onClick={() => setModalActiveTab('code')}
                  style={{
                    ...styles.modalTabBtn,
                    backgroundColor: modalActiveTab === 'code' ? '#0284c7' : '#162442',
                    color: modalActiveTab === 'code' ? '#ffffff' : '#cbd5e1',
                    border: modalActiveTab === 'code' ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.15)',
                  }}
                >
                  💻 Code View
                </button>
                <button
                  onClick={() => {
                    setModalActiveTab('structure');
                    if (!fileStructureData || fileStructureData.file_path !== sourceViewer.file_path) {
                      fetchFileStructure(sourceViewer.file_path);
                    }
                  }}
                  style={{
                    ...styles.modalTabBtn,
                    backgroundColor: modalActiveTab === 'structure' ? '#0284c7' : '#162442',
                    color: modalActiveTab === 'structure' ? '#ffffff' : '#cbd5e1',
                    border: modalActiveTab === 'structure' ? '1px solid #38bdf8' : '1px solid rgba(255, 255, 255, 0.15)',
                  }}
                >
                  📊 AST Structure (Mermaid)
                </button>
              </div>

              <button onClick={() => setSourceViewer(null)} style={styles.closeBtn}>
                ✕ Close
              </button>
            </div>

            <div style={styles.modalBody}>
              {modalActiveTab === 'code' ? (
                <div style={styles.codeEditor}>
                  {sourceViewer.lines && sourceViewer.lines.length > 0 ? (
                    sourceViewer.lines.map((line) => (
                      <div
                        key={line.line_number}
                        style={{
                          ...styles.codeLineRow,
                          backgroundColor: line.is_highlighted ? 'rgba(239, 68, 68, 0.22)' : 'transparent',
                          borderLeft: line.is_highlighted ? '4px solid #ef4444' : '4px solid transparent',
                        }}
                      >
                        <span style={{
                          ...styles.lineNumber,
                          color: line.is_highlighted ? '#fca5a5' : '#64748b',
                          fontWeight: line.is_highlighted ? 700 : 400,
                        }}>
                          {line.line_number}
                        </span>
                        <span style={styles.lineContent}>{line.content || ' '}</span>
                      </div>
                    ))
                  ) : (
                    <div style={styles.emptyStructureBox}>
                      <p>Loading code lines…</p>
                    </div>
                  )}
                </div>
              ) : isLoadingFileStructure ? (
                <div style={styles.structureLoadingBox}>
                  <div style={styles.miniSpinner} />
                  <p style={{ color: '#cbd5e1', marginTop: '0.75rem', fontWeight: 500 }}>
                    Parsing AST symbols and generating Mermaid diagram…
                  </p>
                </div>
              ) : fileStructureData && fileStructureData.file_path === sourceViewer.file_path ? (
                <MermaidViewer
                  syntax={fileStructureData.mermaid_syntax}
                  classDiagramSyntax={fileStructureData.class_diagram_syntax}
                  metrics={fileStructureData.metrics}
                  title={`AST Structure: ${fileStructureData.file_path}`}
                  maxHeight="580px"
                  cardStyle={{ marginTop: 0, border: 'none', background: 'transparent', boxShadow: 'none' }}
                />
              ) : (
                <div style={styles.structureLoadingBox}>
                  <div style={styles.miniSpinner} />
                  <p style={{ color: '#cbd5e1', marginTop: '0.75rem', fontWeight: 500 }}>
                    Loading file structure…
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

// ── Styles (High-Contrast, Modern Developer Aesthetic) ──────────────────────

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#070b14',
    backgroundImage:
      'radial-gradient(ellipse 90% 50% at 50% -10%, rgba(14, 165, 233, 0.16), transparent 70%), radial-gradient(ellipse 50% 30% at 80% 20%, rgba(99, 102, 241, 0.1), transparent 60%)',
    fontFamily: "'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    color: '#f8fafc',
  },
  topNavbar: {
    width: '100%',
    borderBottom: '1px solid rgba(255, 255, 255, 0.12)',
    backgroundColor: 'rgba(7, 11, 20, 0.85)',
    backdropFilter: 'blur(16px)',
    WebkitBackdropFilter: 'blur(16px)',
    position: 'sticky',
    top: 0,
    zIndex: 40,
    padding: '0.75rem 1.5rem',
  },
  navInner: {
    maxWidth: '1120px',
    margin: '0 auto',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    flexWrap: 'wrap',
    gap: '0.75rem',
  },
  navBrand: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.6rem',
  },
  navLogoWrap: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.45rem',
  },
  navLogoIcon: {
    fontSize: '1.25rem',
    filter: 'drop-shadow(0 0 8px rgba(56, 189, 248, 0.6))',
  },
  navLogoTitle: {
    fontSize: '1.25rem',
    fontWeight: 800,
    letterSpacing: '-0.02em',
    color: '#ffffff',
  },
  navVersionBadge: {
    fontSize: '0.7rem',
    fontWeight: 700,
    padding: '0.15rem 0.45rem',
    borderRadius: '6px',
    backgroundColor: 'rgba(56, 189, 248, 0.18)',
    color: '#38bdf8',
    border: '1px solid rgba(56, 189, 248, 0.35)',
  },
  navDivider: {
    color: 'rgba(255, 255, 255, 0.2)',
    fontWeight: 300,
  },
  navTagline: {
    fontSize: '0.85rem',
    color: '#cbd5e1',
    fontWeight: 500,
  },
  navActions: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
  },
  backendStatusPill: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.5rem',
    padding: '0.35rem 0.75rem',
    borderRadius: '9999px',
    border: '1px solid',
    fontSize: '0.8rem',
    fontWeight: 600,
  },
  statusDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    boxShadow: '0 0 8px currentColor',
  },
  statusText: {
    fontSize: '0.78rem',
    fontWeight: 600,
  },
  navLink: {
    fontSize: '0.82rem',
    fontWeight: 600,
    color: '#e2e8f0',
    textDecoration: 'none',
    padding: '0.35rem 0.75rem',
    borderRadius: '8px',
    backgroundColor: '#111c34',
    border: '1px solid rgba(255, 255, 255, 0.12)',
    transition: 'all 0.15s ease',
  },
  container: {
    width: '100%',
    maxWidth: '1120px',
    margin: '0 auto',
    padding: '2rem 1.25rem 4rem 1.25rem',
  },
  card: {
    backgroundColor: '#0d1527',
    border: '1px solid rgba(255, 255, 255, 0.13)',
    borderRadius: '18px',
    padding: '2.25rem',
    boxShadow: '0 24px 60px -15px rgba(0, 0, 0, 0.75), 0 0 40px -10px rgba(14, 165, 233, 0.12)',
  },
  header: {
    marginBottom: '1.75rem',
  },
  logoBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    fontSize: '0.75rem',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.08em',
    padding: '0.3rem 0.75rem',
    borderRadius: '9999px',
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
    color: '#38bdf8',
    border: '1px solid rgba(56, 189, 248, 0.35)',
    marginBottom: '0.85rem',
    boxShadow: '0 0 15px rgba(56, 189, 248, 0.15)',
  },
  title: {
    fontSize: '2rem',
    fontWeight: 800,
    letterSpacing: '-0.03em',
    margin: '0 0 0.5rem 0',
    color: '#ffffff',
    textShadow: '0 2px 10px rgba(0, 0, 0, 0.4)',
  },
  subtitle: {
    color: '#cbd5e1',
    fontSize: '1rem',
    lineHeight: 1.5,
    margin: 0,
    maxWidth: '800px',
  },
  form: {
    display: 'flex',
    gap: '0.75rem',
    marginBottom: '1.75rem',
    flexWrap: 'wrap',
  },
  inputWrapper: {
    flex: '1 1 400px',
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
  },
  inputIcon: {
    position: 'absolute',
    left: '1rem',
    fontSize: '1.05rem',
    color: '#94a3b8',
    pointerEvents: 'none',
  },
  input: {
    width: '100%',
    padding: '0.9rem 1rem 0.9rem 2.8rem',
    borderRadius: '12px',
    border: '1px solid rgba(255, 255, 255, 0.18)',
    backgroundColor: '#070c18',
    color: '#ffffff',
    fontSize: '0.98rem',
    fontFamily: "'JetBrains Mono', monospace",
    outline: 'none',
    boxShadow: 'inset 0 2px 6px rgba(0, 0, 0, 0.4)',
    transition: 'all 0.2s ease',
  },
  buttonGroup: {
    display: 'flex',
    flexShrink: 0,
  },
  button: {
    padding: '0.9rem 1.6rem',
    borderRadius: '12px',
    fontSize: '0.95rem',
    fontWeight: 700,
    cursor: 'pointer',
    border: 'none',
    transition: 'all 0.2s cubic-bezier(0.4, 0, 0.2, 1)',
    letterSpacing: '0.01em',
  },
  btnContent: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.55rem',
  },
  btnSpinner: {
    width: '18px',
    height: '18px',
    border: '2px solid rgba(255, 255, 255, 0.3)',
    borderRadius: '50%',
    borderTopColor: '#ffffff',
    animation: 'spin 0.8s linear infinite',
  },
  primaryButton: {
    background: 'linear-gradient(135deg, #0284c7 0%, #2563eb 50%, #4f46e5 100%)',
    color: '#ffffff',
    boxShadow: '0 4px 20px -2px rgba(2, 132, 199, 0.45)',
  },
  indexButton: {
    background: 'linear-gradient(135deg, #059669 0%, #10b981 100%)',
    color: '#ffffff',
    whiteSpace: 'nowrap',
    boxShadow: '0 4px 18px -2px rgba(16, 185, 129, 0.4)',
  },
  analyzeButton: {
    background: 'linear-gradient(135deg, #e11d48 0%, #be123c 100%)',
    color: '#ffffff',
    whiteSpace: 'nowrap',
    padding: '0.85rem 1.5rem',
    boxShadow: '0 4px 18px -2px rgba(225, 29, 72, 0.45)',
  },
  recentWorkspacesContainer: {
    marginBottom: '1.75rem',
    padding: '1rem 1.25rem',
    borderRadius: '12px',
    backgroundColor: '#080e1d',
    border: '1px solid rgba(255, 255, 255, 0.1)',
  },
  recentHeaderRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '0.65rem',
  },
  recentLabel: {
    fontSize: '0.78rem',
    fontWeight: 700,
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    color: '#38bdf8',
  },
  recentHint: {
    fontSize: '0.75rem',
    color: '#94a3b8',
  },
  recentChips: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '0.6rem',
  },
  recentChip: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.5rem',
    padding: '0.45rem 0.85rem',
    borderRadius: '10px',
    border: '1px solid rgba(255, 255, 255, 0.14)',
    backgroundColor: '#111c34',
    color: '#f8fafc',
    fontSize: '0.85rem',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  frameworkPill: {
    fontSize: '0.7rem',
    fontWeight: 700,
    padding: '0.12rem 0.4rem',
    borderRadius: '5px',
    backgroundColor: 'rgba(56, 189, 248, 0.2)',
    color: '#38bdf8',
    border: '1px solid rgba(56, 189, 248, 0.4)',
  },
  errorBox: {
    backgroundColor: 'rgba(239, 68, 68, 0.10)',
    border: '1px solid rgba(239, 68, 68, 0.45)',
    borderLeft: '5px solid #ef4444',
    borderRadius: '12px',
    padding: '1.4rem',
    marginBottom: '1.75rem',
    boxShadow: '0 10px 30px -5px rgba(239, 68, 68, 0.2)',
  },
  errorHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.6rem',
    marginBottom: '0.65rem',
  },
  errorIcon: {
    fontSize: '1.35rem',
  },
  errorTitle: {
    color: '#fecaca',
    fontWeight: 800,
    fontSize: '1.05rem',
  },
  errorCodeRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    marginBottom: '0.75rem',
  },
  errorCodeLabel: {
    color: '#fca5a5',
    fontSize: '0.85rem',
    fontWeight: 600,
  },
  errorCodeBadge: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '0.82rem',
    backgroundColor: 'rgba(239, 68, 68, 0.25)',
    color: '#ffffff',
    padding: '0.2rem 0.5rem',
    borderRadius: '6px',
    border: '1px solid rgba(239, 68, 68, 0.4)',
  },
  detailsBox: {
    backgroundColor: '#070b14',
    padding: '0.85rem 1rem',
    borderRadius: '10px',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    color: '#fee2e2',
    fontSize: '0.88rem',
    marginBottom: '0.75rem',
  },
  detailsHeading: {
    display: 'block',
    fontWeight: 700,
    color: '#fca5a5',
    marginBottom: '0.3rem',
  },
  detailsText: {
    margin: 0,
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '0.85rem',
    lineHeight: 1.45,
    color: '#fecaca',
  },
  fixBox: {
    backgroundColor: 'rgba(245, 158, 11, 0.12)',
    padding: '0.85rem 1rem',
    borderRadius: '10px',
    border: '1px solid rgba(245, 158, 11, 0.4)',
    color: '#fef08a',
    fontSize: '0.88rem',
  },
  fixHeading: {
    display: 'block',
    fontWeight: 700,
    color: '#fde047',
    marginBottom: '0.3rem',
  },
  fixText: {
    margin: 0,
    lineHeight: 1.45,
    color: '#ffffff',
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '0.85rem',
  },
  repoSection: {
    marginTop: '2rem',
    borderTop: '1px solid rgba(255, 255, 255, 0.12)',
    paddingTop: '2rem',
  },
  repoBanner: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '1.5rem',
    flexWrap: 'wrap',
    gap: '1rem',
  },
  repoName: {
    fontSize: '1.35rem',
    color: '#ffffff',
  },
  workspaceId: {
    fontSize: '0.85rem',
    color: '#cbd5e1',
    marginTop: '0.35rem',
    display: 'flex',
    alignItems: 'center',
    gap: '0.4rem',
  },
  wsIdCode: {
    fontFamily: "'JetBrains Mono', monospace",
    color: '#93c5fd',
    backgroundColor: '#111c34',
    padding: '0.15rem 0.5rem',
    borderRadius: '6px',
    border: '1px solid rgba(255, 255, 255, 0.1)',
  },
  statusBadgeGreen: {
    backgroundColor: 'rgba(16, 185, 129, 0.18)',
    border: '1px solid rgba(16, 185, 129, 0.45)',
    color: '#6ee7b7',
    padding: '0.45rem 0.95rem',
    borderRadius: '9999px',
    fontSize: '0.85rem',
    fontWeight: 700,
    display: 'inline-flex',
    alignItems: 'center',
    gap: '0.5rem',
    boxShadow: '0 0 15px rgba(16, 185, 129, 0.25)',
  },
  pulsingDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    backgroundColor: '#10b981',
    boxShadow: '0 0 8px #10b981',
  },
  statsRow: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '1.25rem',
    marginBottom: '1.75rem',
  },
  statBox: {
    backgroundColor: '#111c34',
    border: '1px solid rgba(255, 255, 255, 0.12)',
    borderRadius: '14px',
    padding: '1.25rem',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    boxShadow: '0 8px 24px rgba(0, 0, 0, 0.35)',
  },
  statVal: {
    fontSize: '1.85rem',
    fontWeight: 800,
    letterSpacing: '-0.02em',
  },
  statLbl: {
    fontSize: '0.8rem',
    color: '#cbd5e1',
    textTransform: 'uppercase',
    letterSpacing: '0.06em',
    marginTop: '0.35rem',
    fontWeight: 600,
  },
  graphLoadingBox: {
    marginTop: '1.5rem',
    padding: '1.75rem',
    backgroundColor: '#111c34',
    border: '1px dashed rgba(56, 189, 248, 0.4)',
    borderRadius: '14px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '0.85rem',
  },
  miniSpinner: {
    width: '20px',
    height: '20px',
    border: '2px solid rgba(56, 189, 248, 0.25)',
    borderTop: '2px solid #38bdf8',
    borderRadius: '50%',
    animation: 'spin 0.8s linear infinite',
  },
  fileExplorerCard: {
    backgroundColor: '#080e1d',
    border: '1px solid rgba(255, 255, 255, 0.12)',
    borderRadius: '16px',
    padding: '1.5rem',
    marginTop: '1.75rem',
    boxShadow: '0 12px 36px rgba(0, 0, 0, 0.5)',
  },
  fileExplorerHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '1.25rem',
    flexWrap: 'wrap',
    gap: '0.75rem',
  },
  explorerTitle: {
    margin: '0 0 0.35rem 0',
    fontSize: '1.25rem',
    fontWeight: 800,
    color: '#ffffff',
  },
  muted: {
    margin: '0.25rem 0 0 0',
    color: '#cbd5e1',
    fontSize: '0.88rem',
    lineHeight: 1.45,
  },
  fileCountPill: {
    fontSize: '0.8rem',
    fontWeight: 700,
    padding: '0.25rem 0.75rem',
    borderRadius: '9999px',
    backgroundColor: '#162442',
    color: '#38bdf8',
    border: '1px solid rgba(56, 189, 248, 0.3)',
  },
  fileExplorerFilterRow: {
    display: 'flex',
    gap: '0.85rem',
    marginBottom: '1.25rem',
    flexWrap: 'wrap',
  },
  fileSearchWrapper: {
    flex: '1 1 280px',
    position: 'relative',
    display: 'flex',
    alignItems: 'center',
  },
  fileSearchIcon: {
    position: 'absolute',
    left: '0.85rem',
    fontSize: '0.95rem',
    color: '#94a3b8',
  },
  fileSearchInput: {
    width: '100%',
    padding: '0.7rem 0.85rem 0.7rem 2.4rem',
    borderRadius: '10px',
    border: '1px solid rgba(255, 255, 255, 0.16)',
    backgroundColor: '#070c18',
    color: '#ffffff',
    fontSize: '0.88rem',
    fontFamily: "'JetBrains Mono', monospace",
    outline: 'none',
  },
  langFilterChips: {
    display: 'flex',
    gap: '0.45rem',
    flexWrap: 'wrap',
    alignItems: 'center',
  },
  langChip: {
    padding: '0.4rem 0.75rem',
    borderRadius: '8px',
    fontSize: '0.75rem',
    fontWeight: 700,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  fileItemsContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.55rem',
    maxHeight: '440px',
    overflowY: 'auto',
    paddingRight: '0.5rem',
  },
  fileItemRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '0.65rem 1rem',
    borderRadius: '10px',
    backgroundColor: '#111c34',
    border: '1px solid rgba(255, 255, 255, 0.08)',
    gap: '0.85rem',
    flexWrap: 'wrap',
    transition: 'all 0.15s ease',
  },
  fileItemInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.65rem',
    flex: '1 1 320px',
    minWidth: 0,
  },
  fileIcon: {
    fontSize: '1.05rem',
    flexShrink: 0,
  },
  filePathText: {
    fontSize: '0.88rem',
    color: '#f8fafc',
    fontFamily: "'JetBrains Mono', monospace",
    fontWeight: 500,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  fileExtBadge: {
    fontSize: '0.72rem',
    fontWeight: 700,
    padding: '0.12rem 0.45rem',
    borderRadius: '5px',
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
    color: '#38bdf8',
    border: '1px solid rgba(56, 189, 248, 0.3)',
    flexShrink: 0,
  },
  fileSizeText: {
    fontSize: '0.78rem',
    color: '#cbd5e1',
    fontWeight: 500,
    flexShrink: 0,
  },
  fileItemActions: {
    display: 'flex',
    gap: '0.5rem',
    alignItems: 'center',
    flexShrink: 0,
  },
  viewStructureBtn: {
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
    border: '1px solid rgba(56, 189, 248, 0.4)',
    color: '#38bdf8',
    borderRadius: '8px',
    padding: '0.4rem 0.8rem',
    fontSize: '0.8rem',
    fontWeight: 700,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  viewCodeBtn: {
    backgroundColor: '#162442',
    border: '1px solid rgba(255, 255, 255, 0.15)',
    color: '#ffffff',
    borderRadius: '8px',
    padding: '0.4rem 0.8rem',
    fontSize: '0.8rem',
    fontWeight: 700,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  moreFilesNotice: {
    textAlign: 'center',
    fontSize: '0.85rem',
    color: '#cbd5e1',
    padding: '1rem 0.5rem',
    fontStyle: 'italic',
  },
  actionCard: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#111c34',
    border: '1px solid rgba(255, 255, 255, 0.12)',
    borderRadius: '16px',
    padding: '1.5rem',
    marginTop: '1.75rem',
    gap: '1.25rem',
    boxShadow: '0 12px 32px rgba(0, 0, 0, 0.4)',
    flexWrap: 'wrap',
  },
  actionInfo: {
    flex: '1 1 340px',
  },
  actionBadge: {
    display: 'inline-block',
    fontSize: '0.72rem',
    fontWeight: 800,
    letterSpacing: '0.06em',
    padding: '0.2rem 0.55rem',
    borderRadius: '6px',
    backgroundColor: 'rgba(16, 185, 129, 0.2)',
    color: '#34d399',
    marginBottom: '0.5rem',
  },
  actionHeading: {
    margin: '0 0 0.4rem 0',
    fontSize: '1.2rem',
    fontWeight: 800,
    color: '#ffffff',
  },
  actionDesc: {
    margin: 0,
    color: '#cbd5e1',
    fontSize: '0.9rem',
    lineHeight: 1.45,
  },
  indexResultCard: {
    display: 'flex',
    alignItems: 'center',
    gap: '1.25rem',
    padding: '1.25rem 1.5rem',
    backgroundColor: 'rgba(16, 185, 129, 0.12)',
    border: '1px solid rgba(16, 185, 129, 0.4)',
    borderRadius: '14px',
    marginTop: '1.25rem',
    boxShadow: '0 8px 24px rgba(16, 185, 129, 0.15)',
  },
  checkIcon: {
    fontSize: '2rem',
  },
  indexResultHeading: {
    margin: '0 0 0.35rem 0',
    fontSize: '1.05rem',
    fontWeight: 800,
    color: '#ffffff',
  },
  indexStats: {
    display: 'flex',
    gap: '1.25rem',
    flexWrap: 'wrap',
  },
  indexStatItem: {
    fontSize: '0.85rem',
    color: '#e2e8f0',
  },
  bugReviewSection: {
    marginTop: '2.5rem',
    borderTop: '1px solid rgba(255, 255, 255, 0.12)',
    paddingTop: '2rem',
  },
  sectionHeading: {
    marginBottom: '1.25rem',
  },
  sectionTitle: {
    margin: '0 0 0.4rem 0',
    fontSize: '1.45rem',
    fontWeight: 800,
    color: '#ffffff',
  },
  sectionSubtitle: {
    margin: 0,
    color: '#cbd5e1',
    fontSize: '0.92rem',
    lineHeight: 1.45,
  },
  queryInputRow: {
    display: 'flex',
    gap: '0.75rem',
    marginBottom: '1rem',
    flexWrap: 'wrap',
  },
  queryInput: {
    flex: '1 1 360px',
    padding: '0.85rem 1.15rem',
    borderRadius: '12px',
    border: '1px solid rgba(255, 255, 255, 0.18)',
    backgroundColor: '#070c18',
    color: '#ffffff',
    fontSize: '0.95rem',
    outline: 'none',
  },
  presetTags: {
    display: 'flex',
    gap: '0.5rem',
    alignItems: 'center',
    flexWrap: 'wrap',
    marginBottom: '1.75rem',
  },
  presetLabel: {
    fontSize: '0.75rem',
    fontWeight: 700,
    color: '#94a3b8',
    letterSpacing: '0.05em',
  },
  presetBtn: {
    fontSize: '0.78rem',
    fontWeight: 600,
    backgroundColor: '#111c34',
    border: '1px solid rgba(255, 255, 255, 0.12)',
    borderRadius: '8px',
    padding: '0.35rem 0.7rem',
    color: '#e2e8f0',
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  findingsContainer: {
    marginTop: '1.75rem',
  },
  findingsHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '1.5rem',
    borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
    paddingBottom: '1rem',
    flexWrap: 'wrap',
    gap: '0.75rem',
  },
  findingsTitle: {
    margin: '0 0 0.35rem 0',
    fontSize: '1.35rem',
    fontWeight: 800,
    color: '#ffffff',
  },
  summaryText: {
    margin: 0,
    color: '#cbd5e1',
    fontSize: '0.92rem',
    lineHeight: 1.5,
    maxWidth: '780px',
  },
  contextBadge: {
    fontSize: '0.8rem',
    fontWeight: 700,
    backgroundColor: 'rgba(56, 189, 248, 0.18)',
    color: '#38bdf8',
    border: '1px solid rgba(56, 189, 248, 0.4)',
    padding: '0.35rem 0.75rem',
    borderRadius: '8px',
  },
  cleanReportBox: {
    display: 'flex',
    alignItems: 'center',
    gap: '1.25rem',
    padding: '1.75rem',
    backgroundColor: 'rgba(16, 185, 129, 0.12)',
    border: '1px solid rgba(16, 185, 129, 0.45)',
    borderRadius: '14px',
  },
  cleanIcon: {
    fontSize: '2.5rem',
  },
  cleanSubtext: {
    margin: '0.35rem 0 0 0',
    color: '#a7f3d0',
    fontSize: '0.9rem',
    lineHeight: 1.45,
  },
  cardsGrid: {
    display: 'flex',
    flexDirection: 'column',
    gap: '1.5rem',
  },
  bugCard: {
    backgroundColor: '#111c34',
    border: '1px solid rgba(255, 255, 255, 0.14)',
    borderRadius: '16px',
    padding: '1.5rem',
    boxShadow: '0 12px 32px rgba(0, 0, 0, 0.4)',
  },
  cardTopRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '1rem',
    flexWrap: 'wrap',
    gap: '0.75rem',
  },
  cardTitleWrap: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    flexWrap: 'wrap',
  },
  sevBadge: {
    fontSize: '0.78rem',
    fontWeight: 800,
    color: '#ffffff',
    padding: '0.3rem 0.65rem',
    borderRadius: '6px',
    letterSpacing: '0.04em',
  },
  findingTitle: {
    margin: 0,
    fontSize: '1.18rem',
    fontWeight: 800,
    color: '#ffffff',
  },
  confPill: {
    fontSize: '0.78rem',
    fontWeight: 700,
    color: '#93c5fd',
    backgroundColor: '#1e293b',
    border: '1px solid rgba(147, 197, 253, 0.3)',
    padding: '0.3rem 0.65rem',
    borderRadius: '6px',
  },
  evidenceRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    marginBottom: '1rem',
    flexWrap: 'wrap',
  },
  evidenceLabel: {
    fontSize: '0.82rem',
    fontWeight: 700,
    color: '#cbd5e1',
  },
  evidenceLinkBtn: {
    backgroundColor: '#070c18',
    border: '1px solid #38bdf8',
    color: '#38bdf8',
    borderRadius: '8px',
    padding: '0.35rem 0.75rem',
    fontSize: '0.82rem',
    fontWeight: 700,
    fontFamily: "'JetBrains Mono', monospace",
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  evidenceStructureBtn: {
    backgroundColor: '#1e1b4b',
    border: '1px solid #818cf8',
    color: '#c7d2fe',
    borderRadius: '8px',
    padding: '0.35rem 0.75rem',
    fontSize: '0.82rem',
    fontWeight: 700,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  fieldBlock: {
    marginBottom: '0.85rem',
  },
  fieldHeading: {
    display: 'block',
    fontSize: '0.85rem',
    fontWeight: 700,
    color: '#cbd5e1',
    marginBottom: '0.25rem',
  },
  fieldContent: {
    margin: 0,
    fontSize: '0.92rem',
    lineHeight: 1.5,
    color: '#f1f5f9',
  },
  rootCauseBox: {
    backgroundColor: 'rgba(239, 68, 68, 0.1)',
    border: '1px solid rgba(239, 68, 68, 0.3)',
    borderRadius: '10px',
    padding: '0.85rem 1rem',
    marginBottom: '0.85rem',
  },
  rootCauseHeading: {
    display: 'block',
    fontSize: '0.85rem',
    fontWeight: 700,
    color: '#fca5a5',
    marginBottom: '0.25rem',
  },
  impactBox: {
    backgroundColor: 'rgba(245, 158, 11, 0.1)',
    border: '1px solid rgba(245, 158, 11, 0.3)',
    borderRadius: '10px',
    padding: '0.85rem 1rem',
    marginBottom: '0.85rem',
  },
  impactHeading: {
    display: 'block',
    fontSize: '0.85rem',
    fontWeight: 700,
    color: '#fcd34d',
    marginBottom: '0.25rem',
  },
  fixSnippetBox: {
    backgroundColor: '#070c18',
    border: '1px solid rgba(56, 189, 248, 0.35)',
    borderRadius: '10px',
    padding: '1rem',
  },
  fixSnippetHeading: {
    display: 'block',
    fontSize: '0.85rem',
    fontWeight: 700,
    color: '#38bdf8',
    marginBottom: '0.4rem',
  },
  fixCode: {
    margin: 0,
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '0.85rem',
    lineHeight: 1.45,
    color: '#f8fafc',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  modalOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(3, 7, 18, 0.85)',
    backdropFilter: 'blur(12px)',
    WebkitBackdropFilter: 'blur(12px)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 999,
    padding: '1.5rem',
  },
  modalContent: {
    backgroundColor: '#0d1527',
    border: '1px solid rgba(255, 255, 255, 0.18)',
    borderRadius: '18px',
    width: '100%',
    maxWidth: '1000px',
    maxHeight: '90vh',
    display: 'flex',
    flexDirection: 'column',
    boxShadow: '0 25px 70px rgba(0, 0, 0, 0.85)',
    overflow: 'hidden',
  },
  modalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '1.25rem 1.5rem',
    borderBottom: '1px solid rgba(255, 255, 255, 0.12)',
    flexWrap: 'wrap',
    gap: '0.85rem',
    backgroundColor: '#111c34',
  },
  modalTitle: {
    margin: 0,
    fontSize: '1.15rem',
    fontWeight: 800,
    color: '#ffffff',
    fontFamily: "'JetBrains Mono', monospace",
  },
  modalSubtitle: {
    margin: 0,
    color: '#cbd5e1',
    fontSize: '0.85rem',
  },
  modalLangBadge: {
    fontSize: '0.72rem',
    fontWeight: 700,
    padding: '0.15rem 0.5rem',
    borderRadius: '5px',
    backgroundColor: 'rgba(56, 189, 248, 0.2)',
    color: '#38bdf8',
    border: '1px solid rgba(56, 189, 248, 0.4)',
  },
  modalTabs: {
    display: 'flex',
    gap: '0.5rem',
    alignItems: 'center',
  },
  modalTabBtn: {
    padding: '0.45rem 0.95rem',
    borderRadius: '8px',
    fontSize: '0.82rem',
    fontWeight: 700,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  closeBtn: {
    backgroundColor: '#1e293b',
    border: '1px solid rgba(255, 255, 255, 0.15)',
    color: '#ffffff',
    padding: '0.45rem 0.85rem',
    borderRadius: '8px',
    cursor: 'pointer',
    fontSize: '0.85rem',
    fontWeight: 700,
  },
  modalBody: {
    padding: '1.25rem',
    overflowY: 'auto',
    flex: 1,
    backgroundColor: '#070c18',
  },
  codeEditor: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '0.88rem',
    backgroundColor: '#050811',
    borderRadius: '10px',
    padding: '0.75rem 0',
    border: '1px solid rgba(255, 255, 255, 0.12)',
  },
  codeLineRow: {
    display: 'flex',
    padding: '0.2rem 1rem',
    lineHeight: 1.5,
  },
  lineNumber: {
    width: '50px',
    textAlign: 'right',
    marginRight: '1.25rem',
    userSelect: 'none',
    flexShrink: 0,
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '0.82rem',
  },
  lineContent: {
    color: '#f8fafc',
    whiteSpace: 'pre',
    overflowX: 'auto',
  },
  structureLoadingBox: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '340px',
    padding: '3rem',
  },
  emptyStructureBox: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    minHeight: '260px',
    color: '#cbd5e1',
    fontStyle: 'italic',
  },
};
