import React from 'react';
import { Header } from '../components/common/Header';
import { Sidebar } from '../components/common/Sidebar';
import { ToastProvider } from '../components/common/Toast';

interface RootLayoutProps {
  children: React.ReactNode;
}

export const RootLayout: React.FC<RootLayoutProps> = ({ children }) => {
  return (
    <ToastProvider>
      <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans antialiased selection:bg-cyan-500 selection:text-slate-950">
        <Header />
        <div className="flex-1 flex w-full max-w-[1600px] mx-auto">
          <Sidebar />
          <main className="flex-1 px-4 sm:px-6 lg:px-8 py-6 max-w-full overflow-x-hidden">
            {children}
          </main>
        </div>
        <footer className="border-t border-slate-900 bg-slate-950/90 py-5 text-center text-xs text-slate-500 mt-auto z-10">
          <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="flex items-center space-x-2">
              <span className="font-semibold text-slate-300">CodeIntel</span>
              <span className="text-slate-600">•</span>
              <span>Developer Codebase Intelligence & ML Issue Analytics</span>
            </div>
            <div className="font-mono text-slate-600 text-[11px] flex items-center space-x-3">
              <span>FastAPI Backend</span>
              <span>•</span>
              <span>TF-IDF + Logistic Reg</span>
              <span>•</span>
              <span>XGBoost Risk Score</span>
              <span>•</span>
              <span>NetworkX AST DAG</span>
            </div>
          </div>
        </footer>
      </div>
    </ToastProvider>
  );
};
