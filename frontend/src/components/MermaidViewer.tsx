/**
 * MermaidViewer Component
 *
 * Renders Mermaid.js diagrams with dark theme styling, zoom/pan controls,
 * high-contrast visual elements, and copy-to-clipboard functionality.
 */

import React, { useEffect, useRef, useState } from 'react';
import mermaid from 'mermaid';

export interface FileStructureMetrics {
  classes?: number;
  methods?: number;
  functions?: number;
  imports?: number;
  internal_calls?: number;
}

interface MermaidViewerProps {
  syntax: string;
  title?: string;
  frameworks?: string[];
  metrics?: FileStructureMetrics;
  classDiagramSyntax?: string;
  maxHeight?: string;
  cardStyle?: React.CSSProperties;
}

// Initialize Mermaid with high-contrast developer theme
mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  securityLevel: 'loose',
  fontFamily: "'JetBrains Mono', 'Plus Jakarta Sans', monospace",
  themeVariables: {
    darkMode: true,
    background: '#070b14',
    primaryColor: '#0369a1',
    primaryTextColor: '#ffffff',
    primaryBorderColor: '#38bdf8',
    lineColor: '#94a3b8',
    secondaryColor: '#162442',
    tertiaryColor: '#0d1527',
    edgeLabelBackground: '#0d1527',
    clusterBkg: '#0d1527',
    clusterBorder: 'rgba(56, 189, 248, 0.4)',
    nodeTextColor: '#ffffff',
  },
});

export const MermaidViewer: React.FC<MermaidViewerProps> = ({
  syntax,
  title,
  frameworks,
  metrics,
  classDiagramSyntax,
  maxHeight,
  cardStyle,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [selectedFormat, setSelectedFormat] = useState<'flowchart' | 'classDiagram'>('flowchart');
  const [svgContent, setSvgContent] = useState<string>('');
  const [renderError, setRenderError] = useState<string | null>(null);
  const [zoom, setZoom] = useState<number>(1);
  const [copied, setCopied] = useState<boolean>(false);

  const activeSyntax =
    selectedFormat === 'classDiagram' && classDiagramSyntax ? classDiagramSyntax : syntax;

  useEffect(() => {
    if (!activeSyntax) return;

    let isMounted = true;
    const renderDiagram = async () => {
      try {
        setRenderError(null);
        const uniqueId = `mermaid-${Math.random().toString(36).substring(2, 9)}`;
        const { svg } = await mermaid.render(uniqueId, activeSyntax);
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
  }, [activeSyntax]);

  const handleCopy = () => {
    navigator.clipboard.writeText(activeSyntax);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleZoomIn = () => setZoom((prev) => Math.min(prev + 0.15, 2.5));
  const handleZoomOut = () => setZoom((prev) => Math.max(prev - 0.15, 0.5));
  const handleResetZoom = () => setZoom(1);

  return (
    <div style={{ ...styles.card, ...(cardStyle || {}) }}>
      {/* Header with Title, Frameworks, and Metrics */}
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

          {metrics && (
            <div style={styles.metricsRow}>
              {metrics.classes !== undefined && (
                <span style={styles.metricPill}>🏛️ {metrics.classes} Classes</span>
              )}
              {metrics.methods !== undefined && metrics.methods > 0 && (
                <span style={styles.metricPill}>⚙️ {metrics.methods} Methods</span>
              )}
              {metrics.functions !== undefined && (
                <span style={styles.metricPill}>⚡ {metrics.functions} Functions</span>
              )}
              {metrics.imports !== undefined && (
                <span style={styles.metricPill}>📦 {metrics.imports} Imports</span>
              )}
              {metrics.internal_calls !== undefined && metrics.internal_calls > 0 && (
                <span style={styles.metricPillHighlight}>🔄 {metrics.internal_calls} Calls</span>
              )}
            </div>
          )}
        </div>

        {/* Action Controls */}
        <div style={styles.controls}>
          {classDiagramSyntax && (
            <div style={styles.formatToggle}>
              <button
                onClick={() => setSelectedFormat('flowchart')}
                style={{
                  ...styles.formatBtn,
                  backgroundColor: selectedFormat === 'flowchart' ? '#0284c7' : '#111c34',
                  color: selectedFormat === 'flowchart' ? '#ffffff' : '#94a3b8',
                }}
              >
                Flowchart
              </button>
              <button
                onClick={() => setSelectedFormat('classDiagram')}
                style={{
                  ...styles.formatBtn,
                  backgroundColor: selectedFormat === 'classDiagram' ? '#0284c7' : '#111c34',
                  color: selectedFormat === 'classDiagram' ? '#ffffff' : '#94a3b8',
                }}
              >
                Class Diagram
              </button>
            </div>
          )}

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
      <div style={{ ...styles.canvasContainer, ...(maxHeight ? { maxHeight } : {}) }}>
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
            <p style={{ color: '#e2e8f0', fontWeight: 500 }}>Rendering architecture diagram…</p>
          </div>
        )}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  card: {
    backgroundColor: '#0d1527',
    border: '1px solid rgba(255, 255, 255, 0.12)',
    borderRadius: '14px',
    padding: '1.5rem',
    marginTop: '1.5rem',
    boxShadow: '0 12px 36px rgba(0, 0, 0, 0.6)',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '1.25rem',
    borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
    paddingBottom: '1rem',
    gap: '1rem',
    flexWrap: 'wrap',
  },
  title: {
    margin: '0 0 0.5rem 0',
    fontSize: '1.2rem',
    fontWeight: 700,
    color: '#ffffff',
    letterSpacing: '-0.01em',
  },
  badgeRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.6rem',
    flexWrap: 'wrap',
  },
  badgeLabel: {
    fontSize: '0.8rem',
    fontWeight: 600,
    color: '#cbd5e1',
    textTransform: 'uppercase',
    letterSpacing: '0.05em',
  },
  badge: {
    backgroundColor: 'rgba(2, 132, 199, 0.25)',
    color: '#38bdf8',
    border: '1px solid rgba(56, 189, 248, 0.45)',
    padding: '0.2rem 0.6rem',
    borderRadius: '6px',
    fontSize: '0.8rem',
    fontWeight: 600,
  },
  controls: {
    display: 'flex',
    gap: '0.5rem',
    alignItems: 'center',
  },
  ctrlBtn: {
    backgroundColor: '#162442',
    border: '1px solid rgba(255, 255, 255, 0.15)',
    color: '#ffffff',
    padding: '0.4rem 0.75rem',
    borderRadius: '8px',
    fontSize: '0.82rem',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
  copyBtn: {
    backgroundColor: '#0284c7',
    border: '1px solid rgba(56, 189, 248, 0.5)',
    color: '#ffffff',
    padding: '0.4rem 0.85rem',
    borderRadius: '8px',
    fontSize: '0.82rem',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
    boxShadow: '0 0 15px rgba(2, 132, 199, 0.3)',
  },
  canvasContainer: {
    backgroundColor: '#050811',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: '10px',
    padding: '1.75rem',
    overflow: 'auto',
    maxHeight: '560px',
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
    gap: '0.85rem',
    color: '#cbd5e1',
    padding: '2.5rem',
  },
  spinner: {
    width: '28px',
    height: '28px',
    border: '3px solid rgba(56, 189, 248, 0.25)',
    borderRadius: '50%',
    borderTopColor: '#38bdf8',
    animation: 'spin 0.8s linear infinite',
  },
  errorBox: {
    padding: '1.25rem',
    backgroundColor: 'rgba(239, 68, 68, 0.12)',
    border: '1px solid rgba(239, 68, 68, 0.4)',
    borderRadius: '10px',
    color: '#fca5a5',
    width: '100%',
  },
  errorTitle: {
    margin: '0 0 0.5rem 0',
    fontWeight: 700,
    color: '#ffffff',
  },
  errorCode: {
    fontFamily: "'JetBrains Mono', monospace",
    fontSize: '0.85rem',
    color: '#fecaca',
  },
  metricsRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    marginTop: '0.6rem',
    flexWrap: 'wrap',
  },
  metricPill: {
    backgroundColor: '#111c34',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    color: '#e2e8f0',
    padding: '0.2rem 0.6rem',
    borderRadius: '6px',
    fontSize: '0.78rem',
    fontWeight: 600,
  },
  metricPillHighlight: {
    backgroundColor: 'rgba(56, 189, 248, 0.18)',
    border: '1px solid rgba(56, 189, 248, 0.4)',
    color: '#38bdf8',
    padding: '0.2rem 0.6rem',
    borderRadius: '6px',
    fontSize: '0.78rem',
    fontWeight: 700,
  },
  formatToggle: {
    display: 'flex',
    borderRadius: '8px',
    overflow: 'hidden',
    border: '1px solid rgba(255, 255, 255, 0.15)',
    marginRight: '0.3rem',
  },
  formatBtn: {
    border: 'none',
    padding: '0.4rem 0.75rem',
    fontSize: '0.8rem',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.15s ease',
  },
};
