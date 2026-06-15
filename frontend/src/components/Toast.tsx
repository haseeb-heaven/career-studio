import { createContext, useContext, useState, useCallback, useEffect } from "react";
import type { ReactNode } from "react";

type ToastType = "success" | "error" | "warning" | "info";

interface Toast {
  id: number;
  type: ToastType;
  title: string;
  message?: string;
}

interface ToastCtx {
  toast: (type: ToastType, title: string, message?: string) => void;
}

const Ctx = createContext<ToastCtx>({ toast: () => {} });

export function useToast() {
  return useContext(Ctx);
}

const STYLES: Record<ToastType, { bar: string; icon: string; title: string; bg: string; border: string }> = {
  success: { bar: "bg-emerald-500", icon: "✅", title: "text-emerald-400", bg: "bg-slate-800", border: "border-emerald-500/30" },
  error:   { bar: "bg-red-500",     icon: "❌", title: "text-red-400",     bg: "bg-slate-800", border: "border-red-500/30" },
  warning: { bar: "bg-amber-500",   icon: "⚠️", title: "text-amber-400",   bg: "bg-slate-800", border: "border-amber-500/30" },
  info:    { bar: "bg-blue-500",    icon: "ℹ️", title: "text-blue-400",    bg: "bg-slate-800", border: "border-blue-500/30" },
};

let _id = 0;

function ToastItem({ t, onDismiss }: { t: Toast; onDismiss: (id: number) => void }) {
  const s = STYLES[t.type];

  useEffect(() => {
    const timer = setTimeout(() => onDismiss(t.id), 5000);
    return () => clearTimeout(timer);
  }, [t.id, onDismiss]);

  return (
    <div
      className={`relative flex items-start gap-3 rounded-xl border ${s.border} ${s.bg} pl-4 pr-4 py-3 shadow-2xl shadow-black/40 w-80 overflow-hidden`}
    >
      <div className={`absolute left-0 top-0 bottom-0 w-1 rounded-l-xl ${s.bar}`} />
      <span className="text-lg shrink-0 mt-0.5">{s.icon}</span>
      <div className="flex-1 min-w-0">
        <p className={`text-sm font-semibold ${s.title}`}>{t.title}</p>
        {t.message && <p className="text-xs text-slate-400 mt-0.5 leading-relaxed">{t.message}</p>}
      </div>
      <button
        onClick={() => onDismiss(t.id)}
        className="text-slate-500 hover:text-slate-300 transition-colors shrink-0 text-lg leading-none"
      >
        ×
      </button>
    </div>
  );
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);

  const dismiss = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const toast = useCallback((type: ToastType, title: string, message?: string) => {
    const id = ++_id;
    setToasts((prev) => [...prev.slice(-4), { id, type, title, message }]);
  }, []);

  return (
    <Ctx.Provider value={{ toast }}>
      {children}
      <div className="fixed bottom-6 right-6 z-[9999] flex flex-col gap-2 items-end">
        {toasts.map((t) => (
          <ToastItem key={t.id} t={t} onDismiss={dismiss} />
        ))}
      </div>
    </Ctx.Provider>
  );
}
