import React, { createContext, useContext, useState } from 'react';
import { CheckCircle2, AlertCircle, Info, X } from 'lucide-react';

interface Toast {
  id: string;
  type: 'success' | 'error' | 'info';
  message: string;
}

interface ToastContextType {
  showToast: (message: string, type?: 'success' | 'error' | 'info') => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const showToast = (message: string, type: 'success' | 'error' | 'info' = 'info') => {
    const id = `toast-${Date.now()}`;
    setToasts((prev) => [...prev, { id, type, message }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      {/* Toast Render Container */}
      <div className="fixed bottom-5 right-5 z-50 flex flex-col space-y-2 max-w-sm pointer-events-none">
        {toasts.map((toast) => (
          <div
            key={toast.id}
            className={`pointer-events-auto flex items-center justify-between p-3.5 rounded-2xl glass-panel border shadow-2xl transition-all text-xs font-semibold ${
              toast.type === 'success'
                ? 'bg-emerald-950/90 text-emerald-300 border-emerald-800'
                : toast.type === 'error'
                ? 'bg-rose-950/90 text-rose-300 border-rose-800'
                : 'bg-slate-900/90 text-cyan-300 border-cyan-800'
            }`}
          >
            <div className="flex items-center space-x-2.5">
              {toast.type === 'success' ? (
                <CheckCircle2 className="h-4 w-4 text-emerald-400 flex-shrink-0" />
              ) : toast.type === 'error' ? (
                <AlertCircle className="h-4 w-4 text-rose-400 flex-shrink-0" />
              ) : (
                <Info className="h-4 w-4 text-cyan-400 flex-shrink-0" />
              )}
              <span>{toast.message}</span>
            </div>
            <button onClick={() => removeToast(toast.id)} className="text-slate-400 hover:text-slate-200 ml-3">
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
};

export const useToast = () => {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used within a ToastProvider');
  return context;
};
