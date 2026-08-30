import React, { createContext, useContext, useState, useCallback } from 'react';
import { cn } from '../../lib/cn';
import { AlertCircle, CheckCircle, Info, X, AlertTriangle } from 'lucide-react';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastItem {
  id: string;
  type: ToastType;
  title?: string;
  message: string;
  duration?: number;
}

interface ToastContextValue {
  showToast: (toast: Omit<ToastItem, 'id'>) => void;
  success: (message: string, title?: string) => void;
  error: (message: string, title?: string) => void;
  warning: (message: string, title?: string) => void;
  info: (message: string, title?: string) => void;
  dismiss: (id: string) => void;
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined);

export const ToastProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [toasts, setToasts] = useState<ToastItem[]>([]);

  const dismiss = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const showToast = useCallback(
    ({ type, title, message, duration = 4000 }: Omit<ToastItem, 'id'>) => {
      const id = Math.random().toString(36).substring(2, 9);
      const newToast: ToastItem = { id, type, title, message, duration };
      setToasts((prev) => [...prev, newToast]);

      if (duration > 0) {
        setTimeout(() => {
          dismiss(id);
        }, duration);
      }
    },
    [dismiss]
  );

  const success = useCallback((message: string, title?: string) => showToast({ type: 'success', message, title }), [showToast]);
  const error = useCallback((message: string, title?: string) => showToast({ type: 'error', message, title, duration: 6000 }), [showToast]);
  const warning = useCallback((message: string, title?: string) => showToast({ type: 'warning', message, title }), [showToast]);
  const info = useCallback((message: string, title?: string) => showToast({ type: 'info', message, title }), [showToast]);

  return (
    <ToastContext.Provider value={{ showToast, success, error, warning, info, dismiss }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-md w-full pointer-events-none px-4">
        {toasts.map((toast) => {
          const icon = {
            success: <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />,
            error: <AlertCircle className="w-5 h-5 text-rose-600 shrink-0 mt-0.5" />,
            warning: <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />,
            info: <Info className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />,
          }[toast.type];

          const bgClasses = {
            success: 'bg-white/85 backdrop-blur-2xl border-white/90 text-slate-900 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.9),0_12px_36px_rgba(16,185,129,0.12)]',
            error: 'bg-white/85 backdrop-blur-2xl border-white/90 text-slate-900 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.9),0_12px_36px_rgba(244,63,94,0.12)]',
            warning: 'bg-white/85 backdrop-blur-2xl border-white/90 text-slate-900 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.9),0_12px_36px_rgba(245,158,11,0.12)]',
            info: 'bg-white/85 backdrop-blur-2xl border-white/90 text-slate-900 shadow-[inset_0_0_0_1px_rgba(255,255,255,0.9),0_12px_36px_rgba(59,130,246,0.12)]',
          }[toast.type];

          return (
            <div
              key={toast.id}
              role="alert"
              className={cn(
                'pointer-events-auto flex items-start gap-3 p-4 rounded-2xl border shadow-xl transition-all duration-200 animate-fade-in',
                bgClasses
              )}
            >
              {icon}
              <div className="flex-1 text-sm">
                {toast.title && <h4 className="font-semibold text-slate-900">{toast.title}</h4>}
                <p className="text-slate-600">{toast.message}</p>
              </div>
              <button
                onClick={() => dismiss(toast.id)}
                className="text-slate-400 hover:text-slate-600 transition-colors p-1"
                aria-label="Dismiss notification"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
};

export function useToast(): ToastContextValue {
  const context = useContext(ToastContext);
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return context;
}
