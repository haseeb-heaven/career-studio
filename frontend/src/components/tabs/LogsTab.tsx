import { useState, useEffect, useCallback } from "react";
import { getLogs, clearLogs } from "../../api";
import type { ActivityLog } from "../../api";
import { useToast } from "../Toast";

const BASE = "http://localhost:8000/api";

interface EnrichedLog extends ActivityLog {
  label?: string;
  severity?: string;
}

const SEVERITY_STYLES: Record<string, { dot: string; badge: string; row: string }> = {
  success: { dot: "bg-emerald-400", badge: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30", row: "" },
  info:    { dot: "bg-blue-400",    badge: "bg-blue-500/15 text-blue-400 border-blue-500/30",       row: "" },
  warning: { dot: "bg-amber-400",   badge: "bg-amber-500/15 text-amber-400 border-amber-500/30",     row: "bg-amber-500/5" },
  error:   { dot: "bg-red-400",     badge: "bg-red-500/15 text-red-400 border-red-500/30",           row: "bg-red-500/5" },
};

const ACTION_ICONS: Record<string, string> = {
  import:       "📥",
  export:       "📤",
  patch:        "✏️",
  delete:       "🗑️",
  analyze:      "📊",
  cover_letter: "✍️",
  roadmap:      "🗺️",
  jobs_search:  "🔍",
  settings:     "⚙️",
  error:        "❌",
};

interface Stats { total: number; by_action: Record<string, number> }

export default function LogsTab() {
  const { toast } = useToast();
  const [logs, setLogs] = useState<EnrichedLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [clearing, setClearing] = useState(false);
  const [stats, setStats] = useState<Stats | null>(null);
  const [filter, setFilter] = useState<string>("all");
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [search, setSearch] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getLogs(500) as EnrichedLog[];
      setLogs(data);
      // Fetch stats
      const s = await fetch(`${BASE}/logs/stats`).then(r => r.json());
      setStats(s);
    } catch {
      toast("error", "Failed to load logs", "Check that the backend is running on port 8000.");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => { load(); }, [load]);

  async function handleClear() {
    if (!confirm("Clear all activity logs? This cannot be undone.")) return;
    setClearing(true);
    try {
      await clearLogs();
      setLogs([]);
      setStats(null);
      toast("success", "Logs cleared", "All activity log entries have been removed.");
    } finally {
      setClearing(false);
    }
  }

  function downloadLog() {
    const a = document.createElement("a");
    a.href = `${BASE}/logs/download`;
    a.download = "career_studio.log";
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  const actions = Array.from(new Set(logs.map(l => l.action)));
  const SEVERITIES = ["info", "success", "warning", "error"];
  const severityCounts = logs.reduce<Record<string, number>>((acc, l) => {
    const sev = l.severity ?? "info";
    acc[sev] = (acc[sev] ?? 0) + 1;
    return acc;
  }, {});

  const filtered = logs.filter(l => {
    if (filter !== "all" && l.action !== filter) return false;
    if (severityFilter !== "all" && (l.severity ?? "info") !== severityFilter) return false;
    if (search && !l.detail?.toLowerCase().includes(search.toLowerCase()) && !l.action.includes(search.toLowerCase())) return false;
    return true;
  });

  return (
    <div className="space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-lg font-semibold text-white">Activity Logs</h2>
          <p className="text-sm text-slate-400 mt-0.5">
            Every action recorded by Career Studio — imports, exports, AI calls, errors.
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <button
            onClick={load}
            disabled={loading}
            className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-1.5 text-xs font-medium text-slate-300 hover:bg-slate-700 disabled:opacity-50 transition-colors"
          >
            {loading ? "Loading…" : "↺ Refresh"}
          </button>
          <button
            onClick={downloadLog}
            className="rounded-lg border border-blue-500/40 bg-blue-500/10 px-3 py-1.5 text-xs font-medium text-blue-300 hover:bg-blue-500/20 transition-colors"
          >
            ⬇ Download .log
          </button>
          <button
            onClick={handleClear}
            disabled={clearing || logs.length === 0}
            className="rounded-lg border border-red-500/40 bg-red-500/10 px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-500/20 disabled:opacity-40 transition-colors"
          >
            {clearing ? "Clearing…" : "🗑 Clear All"}
          </button>
        </div>
      </div>

      {/* Stats cards */}
      {stats && stats.total > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="rounded-xl border border-slate-700/40 bg-slate-800/40 p-3 text-center">
            <p className="text-2xl font-bold text-white">{stats.total}</p>
            <p className="text-xs text-slate-400 mt-0.5">Total Events</p>
          </div>
          {Object.entries(stats.by_action).slice(0, 3).map(([action, count]) => (
            <div key={action} className="rounded-xl border border-slate-700/40 bg-slate-800/40 p-3 text-center">
              <p className="text-2xl font-bold text-white">{count}</p>
              <p className="text-xs text-slate-400 mt-0.5 capitalize">{action.replace("_", " ")}</p>
            </div>
          ))}
        </div>
      )}

      {/* Filter + search bar */}
      {logs.length > 0 && (
        <div className="flex gap-2 flex-wrap">
          <input
            type="text"
            placeholder="Search logs…"
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="flex-1 min-w-40 rounded-lg bg-slate-800 border border-slate-700 px-3 py-1.5 text-sm text-slate-200 placeholder-slate-600 focus:border-blue-500 focus:outline-none"
          />
          <div className="flex gap-1 flex-wrap">
            {["all", ...actions].map(a => (
              <button
                key={a}
                onClick={() => setFilter(a)}
                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition-colors ${
                  filter === a
                    ? "bg-blue-600 text-white"
                    : "border border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200"
                }`}
              >
                {a === "all" ? "All" : (ACTION_ICONS[a] ?? "") + " " + a.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Severity filter bar */}
      {logs.length > 0 && (
        <div className="flex gap-1.5 flex-wrap items-center">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider mr-1">Severity:</span>
          {["all", ...SEVERITIES].map(sev => {
            const st = sev === "all" ? null : SEVERITY_STYLES[sev];
            const count = sev === "all" ? logs.length : (severityCounts[sev] ?? 0);
            return (
              <button
                key={sev}
                onClick={() => setSeverityFilter(sev)}
                disabled={sev !== "all" && count === 0}
                className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors disabled:opacity-30 ${
                  severityFilter === sev
                    ? "bg-blue-600 border-blue-600 text-white"
                    : `border-slate-700 text-slate-400 hover:border-slate-500 hover:text-slate-200 ${st ? "" : ""}`
                }`}
              >
                {st && <span className={`w-1.5 h-1.5 rounded-full ${st.dot}`} />}
                <span className="capitalize">{sev}</span>
                <span className="text-slate-500">({count})</span>
              </button>
            );
          })}
        </div>
      )}

      {/* Log entries */}
      {loading && (
        <div className="flex items-center gap-3 text-sm text-blue-400 animate-pulse py-8 justify-center">
          <span className="text-xl">📋</span> Loading activity logs…
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <div className="rounded-2xl border border-slate-700/40 bg-slate-800/30 py-14 text-center">
          <p className="text-4xl mb-3">📋</p>
          <p className="text-slate-400 text-sm font-medium">
            {logs.length === 0 ? "No activity yet" : "No logs match your filter"}
          </p>
          <p className="text-slate-500 text-xs mt-1">
            {logs.length === 0 ? "Upload a resume and start using the platform to see logs here." : "Try clearing the search or changing the filter."}
          </p>
        </div>
      )}

      {!loading && filtered.length > 0 && (
        <div className="rounded-2xl border border-slate-700/40 overflow-hidden">
          <div className="bg-slate-800/60 px-4 py-2.5 border-b border-slate-700/40 flex items-center gap-2">
            <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
              {filtered.length} of {logs.length} entries
            </span>
          </div>
          <div className="divide-y divide-slate-700/30">
            {filtered.map((entry) => {
              const sev = entry.severity ?? "info";
              const st = SEVERITY_STYLES[sev] ?? SEVERITY_STYLES.info;
              const icon = ACTION_ICONS[entry.action] ?? "•";
              return (
                <div key={entry.id} className={`flex items-start gap-3 px-4 py-3 hover:bg-slate-800/40 transition-colors ${st.row}`}>
                  {/* Severity dot */}
                  <div className="mt-1.5 shrink-0">
                    <div className={`w-2 h-2 rounded-full ${st.dot}`} />
                  </div>

                  {/* Icon + label */}
                  <div className="shrink-0 w-32">
                    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold ${st.badge}`}>
                      <span>{icon}</span>
                      <span className="truncate max-w-20">{entry.label ?? entry.action}</span>
                    </span>
                  </div>

                  {/* Detail */}
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-slate-200 leading-snug">
                      {entry.detail || <span className="text-slate-500 italic">No detail</span>}
                    </p>
                    {entry.profile_id != null && (
                      <p className="text-xs text-slate-500 mt-0.5">Profile #{entry.profile_id}</p>
                    )}
                  </div>

                  {/* Timestamp */}
                  <div className="shrink-0 text-right">
                    <p className="text-xs text-slate-400 whitespace-nowrap">
                      {new Date(entry.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                    </p>
                    <p className="text-xs text-slate-600 whitespace-nowrap">
                      {new Date(entry.created_at).toLocaleDateString()}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
