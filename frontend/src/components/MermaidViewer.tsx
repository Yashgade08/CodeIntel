/**
 * MermaidViewer Component
 *
 * Renders Mermaid.js diagrams with dark theme styling, zoom/pan controls,
 * and copy-to-clipboard functionality.
 */

import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

interface MermaidViewerProps {
  syntax: string;
  title?: string;
  frameworks?: string[];
}

// Initialize Mermaid with dark theme
mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  securityLevel: 'loose',
  fontFamily: "'Inter', system-ui, sans-serif",
  themeVariables: {
    darkMode: true,
    background: '#090e1a',
    primaryColor: '#0284c7',
    primaryTextColor: '#f8fafc',
    primaryBorderColor: '#38bdf8',
    lineColor: '#64748b',
    secondaryColor: '#1e293b',
    tertiaryColor: '#0f172a',
  },
});

export const MermaidViewer: React.FC<MermaidViewerProps> = ({ syntax, title, frameworks }) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [svgContent, setSvgContent] = useState<string>('');
  const [renderError, setRenderError] = useState<string | null>(null);
  const [zoom, setZoom] = useState<number>(1);
  const [copied, setCopied] = useState<boolean>(false);

  useEffect(() => {
    if (!syntax) return;

    let isMounted = true;
    const renderDiagram = async () => {
      try {
        setRenderError(null);
        const uniqueId = `mermaid-${Math.random().toString(36).substring(2, 9)}`;
        const { svg } = await mermaid.render(uniqueId, syntax);
        if (isMounted) {
          setSvgContent(svg);
        }
      } catch (err: unknown) {
        if (isMounted) {
          setRenderError(err instanceof Error ? err.message : String(err));
        }
      }
    };

    renderDiagram();

    return () => {
      isMounted = false;
    };
  }, [syntax]);

  const handleCopy = () => {
    navigator.clipboard.writeText(syntax);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 0.15, 2.5));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 0.15, 0.5));
  const handleResetZoom = () => setZoom(1);

  return (
    <div style={styles.card}>
      {/* Header with Title and Framework Badges */}
      <div style={styles.header}>
        <div>
          <h3 style={styles.title}>{title || '📊 Project Structure & Architecture'}</h3>
          {frameworks && frameworks.length > 0 && (
            <div style={styles.badgeRow}>
              <span style={styles.badgeLabel}>Detected Stack:</span>
              {frameworks.map((fw) => (
                <span key={fw} style={styles.badge}>
                  ⚡ {fw}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* Action Controls */}
        <div style={styles.controls}>
          <button onClick={handleZoomOut} style={styles.ctrlBtn} title="Zoom Out">
            🔍 -
          </button>
          <button onClick={handleResetZoom} style={styles.ctrlBtn} title="Reset Zoom">
            {Math.round(zoom * 100)}%
          </button>
          <button onClick={handleZoomIn} style={styles.ctrlBtn} title="Zoom In">
            🔍 +
          </button>
          <button onClick={handleCopy} style={styles.copyBtn} title="Copy Mermaid Syntax">
            {copied ? '✓ Copied' : '📋 Copy Syntax'}
          </button>
        </div>
      </div>

      {/* Diagram Canvas */}
      <div style={styles.canvasContainer}>
        {renderError ? (
          <div style={styles.errorBox}>
            <p style={styles.errorTitle}>⚠️ Failed to render Mermaid diagram:</p>
            <code style={styles.errorCode}>{renderError}</code>
          </div>
        ) : svgContent ? (
          <div
            ref={containerRef}
            style={{
              ...styles.svgWrapper,
              transform: `scale(${zoom})`,
              transformOrigin: 'top center',
            }}
            dangerouslySetInnerHTML={{ __html: svgContent }}
          />
        ) : (
          <div style={styles.loadingBox}>
            <div style={styles.spinner}></div>
            <p>Rendering architecture diagram…</p>
          </div>
        )}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  card: {
    backgroundColor: '#090e1a',
    border: '1px solid #1e293b',
    borderRadius: '12px',
    padding: '1.25rem',
    marginTop: '1.5rem',
    boxShadow: '0 10px 30px rgba(0, 0, 0, 0.5)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '1rem',
    borderBottom: '1px solid #1e293b',
    paddingBottom: '0.75rem',
    gap: '1rem',
    flexWrap: 'wrap',
  },
  title: {
    margin: '0 0 0.4rem 0',
    fontSize: '1.15rem',
    fontWeight: 700,
    color: '#f8fafc',
  },
  badgeRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    flexWrap: 'wrap',
  },
  badgeLabel: {
    fontSize: '0.75rem',
    color: '#94a3b8',
  },
  badge: {
    backgroundColor: '#03253b',
    color: '#38bdf8',
    border: '1px solid #0284c7',
    padding: '0.15rem 0.5rem',
    borderRadius: '6px',
    fontSize: '0.75rem',
    fontWeight: 600,
  },
  controls: {
    display: 'flex',
    gap: '0.4rem',
    alignItems: 'center',
  },
  ctrlBtn: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    color: '#e2e8f0',
    padding: '0.35rem 0.65rem',
    borderRadius: '6px',
    fontSize: '0.78rem',
    cursor: 'pointer',
  },
  copyBtn: {
    backgroundColor: '#0284c7',
    border: 'none',
    color: '#ffffff',
    padding: '0.35rem 0.75rem',
    borderRadius: '6px',
    fontSize: '0.78rem',
    fontWeight: 600,
    cursor: 'pointer',
  },
  canvasContainer: {
    backgroundColor: '#030712',
    border: '1px solid #1e293b',
    borderRadius: '10px',
    padding: '1.5rem',
    overflow: 'auto',
    maxHeight: '520px',
    display: 'flex',
    justifyContent: 'center',
  },
  svgWrapper: {
    transition: 'transform 0.15s ease-out',
    display: 'flex',
    justifyContent: 'center',
    width: '100%',
  },
  loadingBox: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '0.75rem',
    color: '#94a3b8',
    padding: '2rem',
  },
  spinner: {
    width: '24px',
    height: '24px',
    border: '2px solid rgba(56, 189, 248, 0.3)',
    borderRadius: '50%',
    borderTopColor: '#38bdf8',
    animation: 'spin 0.8s linear infinite',
  },
  errorBox: {
    padding: '1rem',
    backgroundColor: '#200b0b',
    border: '1px solid #991b1b',
    borderRadius: '8px',
    color: '#f87171',
    width: '100%',
  },
  errorTitle: {
    margin: '0 0 0.5rem 0',
    fontWeight: 600,
  },
  errorCode: {
    fontFamily: 'monospace',
    fontSize: '0.8rem',
  },
};
