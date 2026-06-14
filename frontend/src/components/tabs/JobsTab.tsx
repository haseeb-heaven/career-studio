import { useState } from "react";
import { searchJobs } from "../../api";
import type { JobMatch } from "../../api";

interface Props { profileId: number; }

function ScoreBadge({ score }: { score: number }) {
  const color = score >= 70 ? "bg-green-100 text-green-800" : score >= 40 ? "bg-yellow-100 text-yellow-800" : "bg-slate-100 text-slate-600";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${color}`}>
      {score.toFixed(0)}% match
    </span>
  );
}

export default function JobsTab({ profileId }: Props) {
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState("");
  const [jobs, setJobs] = useState<JobMatch[]>([]);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  async function search() {
    setLoading(true);
    setError("");
    try {
      const r = await searchJobs(profileId, 20);
      setQuery(r.query);
      setJobs(r.jobs);
      setSearched(true);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Job search failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">Live Job Matching</h2>
          <p className="text-sm text-slate-500">
            Searches Remotive and Adzuna for jobs matching your skills. Results are scored by keyword overlap.
          </p>
        </div>
        <button
          onClick={search}
          disabled={loading}
          className="rounded-lg bg-blue-700 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50"
        >
          {loading ? "Searching…" : "Find Jobs"}
        </button>
      </div>

      {error && <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">{error}</div>}

      {loading && (
        <p className="text-sm text-blue-600 animate-pulse">🔍 Searching job boards…</p>
      )}

      {query && (
        <p className="text-xs text-slate-500">
          Search query: <span className="font-mono bg-slate-100 px-2 py-0.5 rounded">{query}</span>
        </p>
      )}

      {searched && jobs.length === 0 && !loading && (
        <div className="rounded-lg bg-yellow-50 border border-yellow-200 p-4 text-sm text-yellow-800">
          No jobs found. This can happen if the job APIs are temporarily unavailable or your profile doesn't have enough skills listed.
        </div>
      )}

      <div className="space-y-3">
        {jobs.map((job) => (
          <div key={job.id} className="rounded-xl border border-slate-200 bg-white p-4 hover:border-blue-300 transition-colors">
            <div className="flex items-start justify-between gap-3 flex-wrap">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="font-semibold text-slate-800 text-sm">{job.title}</h3>
                  <ScoreBadge score={job.match_score} />
                  <span className="rounded-full bg-blue-100 text-blue-700 px-2 py-0.5 text-xs">{job.source}</span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  {job.company}
                  {job.location && ` · ${job.location}`}
                </p>
                {job.description && (
                  <p className="text-xs text-slate-600 mt-2 line-clamp-3">{job.description}</p>
                )}
              </div>
              {job.url && (
                <a
                  href={job.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 rounded-lg border border-blue-300 px-3 py-1.5 text-xs font-medium text-blue-700 hover:bg-blue-50"
                >
                  Apply →
                </a>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
