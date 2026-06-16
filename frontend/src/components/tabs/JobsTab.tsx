import { useState } from "react";
import { searchJobs } from "../../api";
import type { JobMatch } from "../../api";
import type { Profile } from "../../types";
import { useToast } from "../Toast";

interface Props {
  profileId: number;
  profile?: Profile;
}

function ScoreBadge({ score }: { score: number }) {
  const color = score >= 70 
    ? "bg-green-500/10 text-green-400 border border-green-500/20" 
    : score >= 40 
      ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20" 
      : "bg-slate-500/10 text-slate-400 border border-slate-600/20";
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${color}`}>
      {score.toFixed(0)}% match
    </span>
  );
}

export default function JobsTab({ profileId, profile }: Props) {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState("");
  const [jobs, setJobs] = useState<JobMatch[]>([]);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  // Filters State - prefilled from profile details if available
  const [jobTitle, setJobTitle] = useState(() => {
    const roles = profile?.experience?.map((e) => e.role).filter(Boolean) || [];
    return roles[0] || "";
  });
  const [location, setLocation] = useState(profile?.location || "");
  const [portal, setPortal] = useState("all");

  async function search() {
    setLoading(true);
    setError("");
    try {
      const r = await searchJobs(profileId, 30, jobTitle, location, portal);
      setQuery(r.query);
      setJobs(r.jobs);
      setSearched(true);
      toast("success", "Jobs found", `${r.jobs.length} positions found`);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Job search failed";
      setError(msg);
      toast("error", "Job search failed", msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">Live Job Matching</h2>
          <p className="text-sm text-slate-400 mt-1">
            Searches LinkedIn, Indeed, Glassdoor, Adzuna, and others for jobs. Scraped results are preferred, with APIs used as a last resort.
          </p>
        </div>
        <button
          onClick={search}
          disabled={loading}
          className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 shadow-md shadow-blue-950/50 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 transition-all"
        >
          {loading ? "Searching…" : "Find Jobs"}
        </button>
      </div>

      {/* 3-Column Filter Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 border border-slate-700/40 bg-slate-800/20 p-5 rounded-2xl">
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5">Job Title / Keywords</label>
          <input
            type="text"
            value={jobTitle}
            onChange={(e) => setJobTitle(e.target.value)}
            placeholder="e.g. Software Engineer"
            className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5">Location</label>
          <input
            type="text"
            value={location}
            onChange={(e) => setLocation(e.target.value)}
            placeholder="e.g. San Francisco, CA"
            className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5">Job Portal</label>
          <select
            value={portal}
            onChange={(e) => setPortal(e.target.value)}
            className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
          >
            <option value="all">All Portals</option>
            <option value="linkedin">LinkedIn (scraped guest API)</option>
            <option value="indeed">Indeed (guest fallback)</option>
            <option value="glassdoor">Glassdoor (guest fallback)</option>
            <option value="adzuna">Adzuna (API configured)</option>
            <option value="remotive">Remotive</option>
            <option value="remoteok">RemoteOK</option>
            <option value="arbeitnow">Arbeitnow</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="rounded-xl bg-red-500/10 border border-red-500/20 p-4 text-sm text-red-300">
          <span className="font-semibold block mb-1">❌ Job search failed</span>
          <p>{error}</p>
        </div>
      )}

      {loading && (
        <div className="flex items-center gap-3 text-sm text-blue-400 animate-pulse">
          <span className="text-xl">🔍</span> Searching job boards…
        </div>
      )}

      {query && (
        <p className="text-xs text-slate-400">
          Search query: <span className="font-mono bg-slate-800 border border-slate-700 px-2 py-0.5 rounded text-blue-400">{query}</span>
        </p>
      )}

      {searched && jobs.length === 0 && !loading && (
        <div className="rounded-xl bg-amber-500/10 border border-amber-500/20 p-4 text-sm text-amber-300">
          No jobs found. This can happen if the job APIs are temporarily unavailable or your profile doesn't have enough skills listed.
        </div>
      )}

      <div className="space-y-3">
        {jobs.map((job) => (
          <div key={job.id} className="rounded-xl border border-slate-700/40 bg-slate-800/30 p-5 hover:border-blue-500/40 hover:bg-slate-800/50 transition-all duration-200">
            <div className="flex items-start justify-between gap-4 flex-wrap">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="font-semibold text-slate-100 text-sm">{job.title}</h3>
                  <ScoreBadge score={job.match_score} />
                  <span className="rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2.5 py-0.5 text-xs uppercase tracking-wide font-medium">{job.source}</span>
                </div>
                <p className="text-xs text-slate-400 mt-1">
                  {job.company}
                  {job.location && ` · ${job.location}`}
                </p>
                {job.description && (
                  <p className="text-xs text-slate-300 mt-3 line-clamp-3 leading-relaxed">{job.description}</p>
                )}
              </div>
              {job.url && (
                <a
                  href={job.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="shrink-0 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-500 hover:scale-[1.02] shadow shadow-blue-950/50 transition-all"
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
