# 🖥️ CodeIntel — Frontend Dashboard (React 19 + TypeScript + Vite)

This is the interactive frontend application for **CodeIntel**, built with **React 19**, **TypeScript 5.7**, **Vite 6**, and **TailwindCSS**.

---

## ⚡ Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Start the Vite development server
npm run dev
```

* **Frontend Dashboard**: [http://localhost:5173](http://localhost:5173)
* By default, the Vite development server proxies all `/api/*` network requests to the FastAPI backend running at `http://127.0.0.1:8000`.

---

## 🎨 Design System & Visual Architecture

The frontend follows a modern, high-contrast developer aesthetic tailored for deep focus and readability:

* **Typography**:
  * **Plus Jakarta Sans**: Primary typeface for UI headings, forms, chips, and body copy.
  * **JetBrains Mono**: Monospace typeface for source code lines, line numbers, file paths, repository identifiers, and commands.
* **Glassmorphism & Surfaces**:
  * High-contrast dark surfaces (`#070b14`, `#0d1527`, `#111c34`) with crisp glass borders (`rgba(255, 255, 255, 0.12)`).
  * WCAG-compliant text contrast ratios (`#ffffff` for headings, `#cbd5e1` for body copy, `#38bdf8` for accents).
* **Live Backend Indicator**:
  * The sticky top navigation bar continuously polls `/api/health` and displays a real-time status pill (`🟢 FastAPI Online (8000)` or `🔴 FastAPI Offline`).

---

## 📁 Frontend File Structure

```text
frontend/
├── src/
│   ├── components/
│   │   └── MermaidViewer.tsx      # Renders interactive Mermaid architecture and AST diagrams
│   ├── pages/
│   │   └── GitHubValidatePage.tsx # Main application dashboard containing:
│   │                              #   - GitHub clone & file discovery bar
│   │                              #   - Recent workspaces quick-switcher
│   │                              #   - High-contrast error diagnostics banner
│   │                              #   - ChromaDB vector indexing trigger
│   │                              #   - AI bug review findings with severity triage
│   │                              #   - File architecture & AST explorer
│   │                              #   - Modal source code viewer with highlighted bug lines
│   ├── index.css                  # High-contrast CSS tokens, glassmorphism, & animations
│   ├── App.tsx                    # Root application component
│   └── main.tsx                   # React DOM root mounting
├── index.html                     # HTML shell importing Plus Jakarta Sans & JetBrains Mono
├── package.json                   # Dependencies & build scripts
├── tailwind.config.js             # Tailwind typography & surface color definitions
└── vite.config.ts                 # Vite bundler configuration & backend API proxy
```

---

## 🛠️ Available Scripts

| Script | Command | Purpose |
| :--- | :--- | :--- |
| **Development** | `npm run dev` | Starts Vite dev server with Hot Module Replacement (HMR) |
| **Type Check** | `npx tsc --noEmit` | Validates TypeScript types across the entire project |
| **Production Build** | `npm run build` | Compiles and minifies assets into the `dist/` directory |
| **Preview Build** | `npm run preview` | Locally serves the production `dist/` build |

---

## 🔌 API Proxy Configuration

In `vite.config.ts`, network requests matching `/api` are automatically forwarded to FastAPI:

```typescript
export default defineConfig({
  server: {
    port: 5173,
    host: true,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
});
```
