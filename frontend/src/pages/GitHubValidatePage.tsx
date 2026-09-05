/**
 * GitHubValidatePage
 *
 * ONE page. ONE purpose:
 *   - Accept a GitHub repository URL from the user.
 *   - Send it to POST /api/github/validate.
 *   - Display the structured success or error response.
 *
 * No mock data. No fallbacks. No silent failures.
 * If the backend is unreachable, that fact is shown explicitly.
 */

import React, { useState } from 'react';

// ── Types matching the backend contract ─────────────────────────────────────

interface ValidateSuccess {
  success: true;
  url: string;
  owner: string;
  repository: string;
}

interface ValidateFailure {
  success: false;
  error: {
    code: string;
    message: string;
  };
}

type ValidateResult = ValidateSuccess | ValidateFailure;

type PageState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: ValidateSuccess }
  | { status: 'error'; message: string }   // network / server error
  | { status: 'invalid'; code: string; message: string }; // backend validation error

// ── Component ────────────────────────────────────────────────────────────────

export const GitHubValidatePage: React.FC = () => {
  const [url, setUrl] = useState('');
  const [state, setState] = useState<PageState>({ status: 'idle' });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Guard: do not send if already loading
    if (state.status === 'loading') return;

    setState({ status: 'loading' });

    try {
      const response = await fetch('/api/github/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: url.trim() }),
      });

      // Parse the response body regardless of HTTP status
      const data: ValidateResult = await response.json();

      if (data.success) {
        setState({ status: 'success', data });
      } else {
        setState({
          status: 'invalid',
          code: data.error.code,
          message: data.error.message,
        });
      }
    } catch (err: unknown) {
      // Network error or backend not reachable — show it explicitly
      const message =
        err instanceof Error
          ? err.message
          : 'Could not reach the backend. Is the server running on port 8000?';
      setState({ status: 'error', message });
    }
  };

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        {/* Header */}
        <h1 style={styles.title}>CodeIntel</h1>
        <p style={styles.subtitle}>GitHub Repository Analyzer</p>

        {/* Input form */}
        <form onSubmit={handleSubmit} style={styles.form}>
          <input
            id="github-url-input"
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/owner/repository"
            style={styles.input}
            disabled={state.status === 'loading'}
            autoFocus
          />
          <button
            id="analyze-button"
            type="submit"
            disabled={state.status === 'loading'}
            style={styles.button}
          >
            {state.status === 'loading' ? 'Validating…' : 'Analyze Repository'}
          </button>
        </form>

        {/* Result area */}
        <div id="result-area" style={styles.resultArea}>
          {state.status === 'idle' && null}

          {state.status === 'loading' && (
            <p style={styles.loading}>Sending to backend…</p>
          )}

          {state.status === 'success' && (
            <div id="result-success" style={styles.success}>
              <p style={styles.successIcon}>✅ Valid GitHub Repository</p>
              <table style={styles.table}>
                <tbody>
                  <tr>
                    <td style={styles.tdLabel}>Owner</td>
                    <td style={styles.tdValue}>{state.data.owner}</td>
                  </tr>
                  <tr>
                    <td style={styles.tdLabel}>Repository</td>
                    <td style={styles.tdValue}>{state.data.repository}</td>
                  </tr>
                  <tr>
                    <td style={styles.tdLabel}>URL</td>
                    <td style={styles.tdValue}>
                      <a
                        href={state.data.url}
                        target="_blank"
                        rel="noreferrer"
                        style={styles.link}
                      >
                        {state.data.url}
                      </a>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          )}

          {state.status === 'invalid' && (
            <div id="result-invalid" style={styles.errorBox}>
              <p style={styles.errorIcon}>❌ Invalid GitHub Repository</p>
              <p style={styles.errorMessage}>{state.message}</p>
              <p style={styles.errorCode}>Error code: {state.code}</p>
            </div>
          )}

          {state.status === 'error' && (
            <div id="result-network-error" style={styles.errorBox}>
              <p style={styles.errorIcon}>⚠️ Request Failed</p>
              <p style={styles.errorMessage}>{state.message}</p>
              <p style={styles.errorCode}>
                Make sure the backend is running: uvicorn app.main:app --port 8000
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// ── Inline styles (no dependency on Tailwind or any external CSS) ─────────────

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#0f172a',
    fontFamily: "'Inter', system-ui, sans-serif",
    padding: '1rem',
  },
  card: {
    backgroundColor: '#1e293b',
    border: '1px solid #334155',
    borderRadius: '12px',
    padding: '2.5rem',
    width: '100%',
    maxWidth: '560px',
    boxShadow: '0 25px 50px rgba(0,0,0,0.5)',
  },
  title: {
    color: '#f1f5f9',
    fontSize: '2rem',
    fontWeight: 800,
    margin: '0 0 0.25rem 0',
    letterSpacing: '-0.5px',
  },
  subtitle: {
    color: '#94a3b8',
    fontSize: '0.95rem',
    margin: '0 0 2rem 0',
  },
  form: {
    display: 'flex',
    flexDirection: 'column',
    gap: '0.75rem',
  },
  input: {
    padding: '0.75rem 1rem',
    borderRadius: '8px',
    border: '1px solid #475569',
    backgroundColor: '#0f172a',
    color: '#f1f5f9',
    fontSize: '0.9rem',
    outline: 'none',
  },
  button: {
    padding: '0.75rem 1.5rem',
    borderRadius: '8px',
    border: 'none',
    background: 'linear-gradient(90deg, #06b6d4, #6366f1)',
    color: '#fff',
    fontWeight: 700,
    fontSize: '0.9rem',
    cursor: 'pointer',
  },
  resultArea: {
    marginTop: '1.5rem',
  },
  loading: {
    color: '#94a3b8',
    fontSize: '0.9rem',
  },
  success: {
    backgroundColor: '#052e16',
    border: '1px solid #166534',
    borderRadius: '8px',
    padding: '1rem 1.25rem',
  },
  successIcon: {
    color: '#4ade80',
    fontWeight: 700,
    marginBottom: '0.75rem',
    fontSize: '1rem',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
  },
  tdLabel: {
    color: '#86efac',
    fontWeight: 600,
    fontSize: '0.85rem',
    padding: '0.3rem 0.75rem 0.3rem 0',
    whiteSpace: 'nowrap',
    verticalAlign: 'top',
  },
  tdValue: {
    color: '#f1f5f9',
    fontSize: '0.9rem',
    padding: '0.3rem 0',
    wordBreak: 'break-all',
  },
  link: {
    color: '#38bdf8',
    textDecoration: 'none',
  },
  errorBox: {
    backgroundColor: '#1c0a0a',
    border: '1px solid #7f1d1d',
    borderRadius: '8px',
    padding: '1rem 1.25rem',
  },
  errorIcon: {
    color: '#f87171',
    fontWeight: 700,
    fontSize: '1rem',
    marginBottom: '0.5rem',
  },
  errorMessage: {
    color: '#fca5a5',
    fontSize: '0.9rem',
    margin: '0 0 0.25rem 0',
  },
  errorCode: {
    color: '#6b7280',
    fontSize: '0.78rem',
    fontFamily: 'monospace',
    margin: 0,
  },
};
