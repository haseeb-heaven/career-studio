import { useState, useEffect, useCallback } from "react";
import { getLogs, clearLogs } from "../../api";
import type { ActivityLog } from "../../api";

const ACTION_COLORS: Record<string, string> = {
  import:       "bg-blue-100 text-blue-800",
  export:       "bg-teal-100 text-teal-800",
  patch:        "bg-purple-100 text-purple-800",
  delete:       "bg-red-100 text-red-800",
  analyze:      "bg-yellow-100 text-yellow-800",
  cover_letter: "bg-pink-100 text-pink-800",
  roadmap:      "bg-indigo-100 text-indigo-800",
  jobs_search:  "bg-green-100 text-green-800",
};

export default function LogsTab() {
  const [logs, setLogs] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [clearing, setClearing] = useState(false);

  const load = useCallback(() => {
    setLoading(true);
    getLogs(200)
      .then(setLogs)
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleClear() {
    if (!confirm("Clear all activity logs?")) return;
    setClearing(true);
    await clearLogs();
    setLogs([]);
    setClearing(false);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">Activity Logs</h2>
          <p className="text-sm text-slate-500">All actions recorded by Career Studio.</p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={load}
            className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-medium text-slate-600 hover:bg-slate-50"
          >
            Refresh
          </button>
          <button
            onClick={handleClear}
            disabled={clearing || logs.length === 0}
            className="rounded-lg border border-red-300 px-3 py-1.5 text-xs font-medium text-red-600 hover:bg-red-50 disabled:opacity-40"
          >
            {clearing ? "Clearing…" : "Clear All"}
          </button>
        </div>
      </div>

      {loading && <p className="text-sm text-blue-600 animate-pulse">Loading logs…</p>}

      {!loading && logs.length === 0 && (
        <div className="rounded-lg bg-slate-50 border border-slate-200 p-6 text-center text-sm text-slate-500">
          No activity logs yet. Start uploading and editing your profile to see logs here.
        </div>
      )}

      {!loading && logs.length > 0 && (
        <div className="overflow-hidden rounded-xl border border-slate-200">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-xs text-slate-500 uppercase">
              <tr>
                <th className="px-4 py-3 text-left">Action</th>
                <th className="px-4 py-3 text-left">Detail</th>
                <th className="px-4 py-3 text-left">Profile</th>
                <th className="px-4 py-3 text-left">Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${ACTION_COLORS[log.action] ?? "bg-slate-100 text-slate-700"}`}>
                      {log.action}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-600 max-w-xs truncate">{log.detail || "—"}</td>
                  <td className="px-4 py-3 text-slate-500">
                    {log.profile_id != null ? `#${log.profile_id}` : "—"}
                  </td>
                  <td className="px-4 py-3 text-slate-400 whitespace-nowrap text-xs">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
