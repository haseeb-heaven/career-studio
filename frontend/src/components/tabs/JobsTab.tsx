import { useState, useEffect, useRef } from "react";
import {
  searchJobs,
  listSavedFilters,
  createSavedFilter,
  updateSavedFilter,
  deleteSavedFilter,
  getExternalSearchLinks,
  fetchResumeKeywords,
  type JobMatch,
  type SavedFilter,
  type ExternalSearchLink,
  type JobSearchOptions,
  type ResumeKeyword,
  type SkillDetail,
  type Gaps,
  type GapEntry,
} from "../../api";
import type { Profile } from "../../types";
import { useToast } from "../Toast";

const STORAGE_KEY = (profileId: number) => `jobsTab.state.v1.${profileId}`;

interface PersistedState {
  jobTitle: string;
  location: string;
  portal: string;
  minYears: number;
  maxYears: number;
  datePosted: "any" | "last_24h" | "last_7d" | "last_30d";
  minMatchScore: number;
  jobTypeChips: string[];
  minSalary: number;
  maxSalary: number;
  salaryCurrency: string;
  experienceLevel: string;
  workTypeFilter: string;
  industryChips: string[];
  sort: "best_match" | "recent" | "salary" | "location";
  jobs: JobMatch[];
  total: number;
  hasMore: boolean;
  queryEcho: string;
  searched: boolean;
  externalLinks: ExternalSearchLink[];
  externalKeywords: string;
  externalLocation: string;
  showAdvanced: boolean;
}

function loadPersisted(profileId: number): Partial<PersistedState> | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY(profileId));
    if (!raw) return null;
    return JSON.parse(raw) as Partial<PersistedState>;
  } catch {
    return null;
  }
}

function savePersisted(profileId: number, state: PersistedState) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(STORAGE_KEY(profileId), JSON.stringify(state));
  } catch {
    // Quota exceeded or storage disabled — silently ignore
  }
}

interface Props {
  profileId: number;
  profile?: Profile;
}

const JOB_TYPES = ["full-time", "part-time", "contract", "remote", "hybrid"] as const;
const INDUSTRY_CHOICES = ["tech", "finance", "healthcare", "education", "retail", "media"];

function MatchGauge({ score }: { score: number }) {
  const radius = 18;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(score, 100) / 100) * circumference;
  const band =
    score >= 85 ? "emerald" : score >= 70 ? "green" : score >= 50 ? "amber" : score >= 30 ? "orange" : "red";
  const palette: Record<string, { ring: string; text: string; chip: string; glow: string }> = {
    emerald: { ring: "stroke-emerald-400", text: "text-emerald-300", chip: "bg-emerald-500/10 border-emerald-500/30 text-emerald-300", glow: "shadow-emerald-900/30" },
    green:   { ring: "stroke-green-400",   text: "text-green-300",   chip: "bg-green-500/10 border-green-500/30 text-green-300",     glow: "shadow-green-900/30" },
    amber:   { ring: "stroke-amber-400",   text: "text-amber-300",   chip: "bg-amber-500/10 border-amber-500/30 text-amber-300",     glow: "shadow-amber-900/20" },
    orange:  { ring: "stroke-orange-400",  text: "text-orange-300",  chip: "bg-orange-500/10 border-orange-500/30 text-orange-300",   glow: "shadow-orange-900/20" },
    red:     { ring: "stroke-red-400",     text: "text-red-300",     chip: "bg-red-500/10 border-red-500/30 text-red-300",           glow: "shadow-red-900/20" },
  };
  const c = palette[band];
  return (
    <span className={`inline-flex items-center gap-2 rounded-full px-2.5 py-1 border text-xs font-semibold shadow-sm ${c.chip} ${c.glow}`}>
      <svg width="26" height="26" viewBox="0 0 48 48" className="-rotate-90">
        <circle cx="24" cy="24" r={radius} fill="none" stroke="currentColor" strokeWidth="4" opacity="0.15" className={c.text} />
        <circle
          cx="24" cy="24" r={radius} fill="none"
          strokeWidth="4" strokeLinecap="round"
          className={`${c.ring} transition-[stroke-dashoffset] duration-1000 ease-out`}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <span className="tabular-nums text-sm">{score.toFixed(0)}%</span>
    </span>
  );
}

function ScoreBreakdown({ breakdown }: { breakdown: Record<string, number> }) {
  const labels: Record<string, string> = {
    skills: "Skills",
    semantic: "Semantic",
    neural_semantic: "Deep Semantic (local AI)",
    keyword_density: "Resume Keywords",
    years: "Experience",
    seniority: "Seniority",
    education: "Education",
    certifications: "Certifications",
    title: "Title match",
    location: "Location",
  };
  return (
    <div className="grid grid-cols-1 gap-1.5 text-xs">
      {Object.entries(labels)
        .filter(([k]) => k !== "neural_semantic" || breakdown[k] !== undefined)
        .map(([k, label]) => {
          const v = breakdown[k] ?? 0;
          const barColor = v >= 70 ? "bg-green-500" : v >= 50 ? "bg-amber-500" : v >= 30 ? "bg-orange-500" : "bg-slate-600";
          return (
            <div key={k} className="flex items-center gap-2">
              <span className="text-slate-400 w-28 shrink-0">{label}</span>
              <div className="flex-1 h-2 bg-slate-700/70 rounded-full overflow-hidden">
                <div
                  className={`h-full ${barColor} transition-all duration-700 ease-out`}
                  style={{ width: `${v}%` }}
                />
              </div>
              <span className="text-slate-300 w-9 text-right tabular-nums">{v.toFixed(0)}</span>
            </div>
          );
        })}
    </div>
  );
}

function SkillDetailList({ details }: { details: SkillDetail[] }) {
  if (!details || details.length === 0) return null;
  const statusMeta: Record<SkillDetail["status"], { icon: string; label: string; cls: string }> = {
    matched: { icon: "✓", label: "Matched",   cls: "text-green-300" },
    partial: { icon: "≈", label: "Partial",   cls: "text-amber-300" },
    missing: { icon: "✗", label: "Missing",   cls: "text-red-300" },
    extra:   { icon: "+", label: "Extra",     cls: "text-slate-400" },
  };
  return (
    <div className="space-y-1.5">
      <p className="text-xs font-semibold text-slate-300">Per-skill match breakdown</p>
      <div className="space-y-1">
        {details.map((d) => {
          const meta = statusMeta[d.status];
          const barColor = d.confidence >= 85 ? "bg-green-500" : d.confidence >= 60 ? "bg-amber-500" : d.confidence >= 30 ? "bg-orange-500" : "bg-slate-600";
          return (
            <div key={`${d.skill}-${d.status}`} className="flex items-center gap-2 text-xs">
              <span className={`w-4 text-center font-bold ${meta.cls}`} title={meta.label}>{meta.icon}</span>
              <span className="w-32 shrink-0 truncate text-slate-200" title={d.skill}>{d.skill}</span>
              {d.category && (
                <span className="shrink-0 rounded bg-slate-700/60 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-slate-400">{d.category}</span>
              )}
              <div className="flex-1 h-1.5 bg-slate-700/60 rounded-full overflow-hidden">
                <div className={`h-full ${barColor} transition-all duration-700`} style={{ width: `${d.confidence}%` }} />
              </div>
              <span className="w-8 text-right tabular-nums text-slate-400">{d.confidence}%</span>
              {d.status === "partial" && d.via && (
                <span className="shrink-0 text-[10px] text-amber-400/80" title={`Covered by related skill: ${d.via}`}>via {d.via}</span>
              )}
              {d.severity === "required" && d.status !== "matched" && (
                <span className="shrink-0 rounded bg-red-500/10 px-1 py-0.5 text-[10px] text-red-400">required</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function GapsPanel({ gaps }: { gaps: Gaps }) {
  if (!gaps) return null;
  const order: Array<keyof Gaps> = ["skills", "experience", "location", "seniority", "education", "certifications"];
  const labels: Record<string, string> = {
    skills: "Skills", experience: "Experience", location: "Location",
    seniority: "Seniority", education: "Education", certifications: "Certifications",
  };
  const statusMeta: Record<GapEntry["status"], { icon: string; cls: string; chip: string }> = {
    ok:   { icon: "✓", cls: "text-green-300",  chip: "bg-green-500/10 border-green-500/20 text-green-300" },
    weak: { icon: "≈", cls: "text-amber-300",  chip: "bg-amber-500/10 border-amber-500/20 text-amber-300" },
    gap:  { icon: "✗", cls: "text-red-300",    chip: "bg-red-500/10 border-red-500/20 text-red-300" },
  };
  const entries = order.map((k) => [k, gaps[k]] as const).filter(([, v]) => v);
  if (entries.length === 0) return null;
  const hasGaps = entries.some(([, v]) => v && v.status !== "ok");
  return (
    <div className="rounded-lg bg-slate-900/60 border border-slate-700/40 p-3">
      <p className="text-xs font-semibold text-slate-300 mb-2 flex items-center gap-1.5">
        <span className="text-slate-400">🧩</span>
        {hasGaps ? "What doesn't match perfectly" : "Match completeness"}
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {entries.map(([key, v]) => {
          if (!v) return null;
          const meta = statusMeta[v.status];
          return (
            <div key={key} className="flex items-start gap-2 rounded-md bg-slate-800/40 border border-slate-700/30 px-2.5 py-2">
              <span className={`mt-0.5 text-sm font-bold ${meta.cls}`}>{meta.icon}</span>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-200">{labels[key]}</span>
                  <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold uppercase border ${meta.chip}`}>{v.status}</span>
                </div>
                <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">{v.message}</p>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function JobCard({ job }: { job: JobMatch }) {
  const [expanded, setExpanded] = useState(false);
  const hasBreakdown = job.match_breakdown && Object.keys(job.match_breakdown).length > 0;
  const matched = job.matched_skills ?? [];
  const missing = job.missing_skills ?? [];
  const skillDetails = job.skill_details ?? [];
  const gaps = job.gaps;
  const gapsGapCount = gaps
    ? Object.values(gaps).filter((g) => g && g.status === "gap").length
    : 0;
  const gapsWeakCount = gaps
    ? Object.values(gaps).filter((g) => g && g.status === "weak").length
    : 0;
  const canExpand = hasBreakdown || skillDetails.length > 0 || !!gaps;
  const hireLabel = job.hire_chance_label ?? "";
  const hireColor = hireLabel === "Very High" || hireLabel === "High"
    ? "bg-green-500/10 text-green-400 border border-green-500/20"
    : hireLabel === "Medium"
      ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20"
      : "bg-red-500/10 text-red-400 border border-red-500/20";
  const confidence = job.confidence ?? "";
  const confidenceColor = confidence === "Excellent"
    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
    : confidence === "Strong"
      ? "bg-green-500/10 text-green-400 border border-green-500/20"
      : confidence === "Moderate"
        ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20"
        : "bg-slate-500/10 text-slate-400 border border-slate-600/20";

  return (
    <div className="rounded-xl border border-slate-700/40 bg-slate-800/30 p-5 hover:border-blue-500/40 hover:bg-slate-800/50 transition-all duration-200">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-semibold text-slate-100 text-sm">{job.title}</h3>
            <button
              type="button"
              onClick={() => canExpand && setExpanded((e) => !e)}
              className={canExpand ? "cursor-pointer" : "cursor-default"}
              title={canExpand ? "Click to see the full match analysis" : ""}
            >
              <MatchGauge score={job.match_score} />
            </button>
            {gapsGapCount > 0 && (
              <span className="rounded-full bg-red-500/10 text-red-400 border border-red-500/20 px-2.5 py-0.5 text-xs font-semibold" title="Number of dimensions that don't match">
                🧩 {gapsGapCount} gap{gapsGapCount > 1 ? "s" : ""}
              </span>
            )}
            {gapsWeakCount > 0 && (
              <span className="rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2.5 py-0.5 text-xs font-semibold" title="Dimensions partially matching">
                ≈ {gapsWeakCount} partial
              </span>
            )}
            {hireLabel && (
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${hireColor}`}>
                🎯 {job.hire_chance}% chance{hireLabel && ` · ${hireLabel}`}
              </span>
            )}
            {confidence && (
              <span className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${confidenceColor}`}>
                📊 {confidence}
              </span>
            )}
            <span className="rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20 px-2.5 py-0.5 text-xs uppercase tracking-wide font-medium">
              {job.source}
            </span>
            {job.is_remote && (
              <span className="rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2.5 py-0.5 text-xs uppercase tracking-wide font-medium">
                Remote
              </span>
            )}
            {job.is_deep_link && (
              <span className="rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20 px-2.5 py-0.5 text-xs uppercase tracking-wide font-medium">
                External
              </span>
            )}
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {job.company}
            {job.location && ` · ${job.location}`}
            {job.date_posted && ` · ${job.date_posted}`}
            {job.salary && ` · ${job.salary}`}
          </p>
          {/* AI insight line */}
          {job.insight && (
            <div className="mt-3 bg-blue-900/20 border border-blue-500/20 rounded-lg p-3">
              <p className="text-xs text-blue-300 flex items-start gap-2 leading-relaxed">
                <span className="text-blue-400 shrink-0 text-sm mt-0.5">🤖</span>
                <span className="flex-1">
                  <strong className="text-blue-200 font-semibold block mb-1">Advanced ML Insight</strong>
                  {job.insight}
                </span>
              </p>
            </div>
          )}
          {(job.job_type || job.industry) && (
            <p className="text-xs text-slate-500 mt-0.5">
              {job.job_type && `Type: ${job.job_type}`}
              {job.job_type && job.industry && " · "}
              {job.industry && `Industry: ${job.industry}`}
            </p>
          )}
          {job.description && (
            <p className="text-xs text-slate-300 mt-3 line-clamp-3 leading-relaxed">{job.description}</p>
          )}

          {(matched.length > 0 || missing.length > 0) && (
            <div className="mt-3 space-y-1.5">
              {matched.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-xs text-green-400/80 font-semibold mr-1">Matched Skills:</span>
                  {matched.map((s) => (
                    <span
                      key={s}
                      className="rounded-md bg-green-500/10 text-green-300 border border-green-500/30 px-2 py-0.5 text-xs shadow-sm shadow-green-900/20"
                    >
                      ✓ {s}
                    </span>
                  ))}
                </div>
              )}
              {missing.length > 0 && (
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="text-xs text-red-400/80 font-semibold mr-1">Missing Skills:</span>
                  {missing.map((s) => (
                    <span
                      key={s}
                      className="rounded-md bg-red-500/10 text-red-300 border border-red-500/30 px-2 py-0.5 text-xs shadow-sm shadow-red-900/20"
                    >
                      ✗ {s}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {expanded && hasBreakdown && (
            <div className="mt-4 rounded-lg bg-slate-900/60 border border-slate-700/40 p-3">
              <p className="text-xs font-semibold text-slate-300 mb-2">Why this score? (9-factor weighted model)</p>
              <ScoreBreakdown breakdown={job.match_breakdown!} />
            </div>
          )}

          {expanded && skillDetails.length > 0 && (
            <div className="mt-3 rounded-lg bg-slate-900/60 border border-slate-700/40 p-3">
              <SkillDetailList details={skillDetails} />
            </div>
          )}

          {expanded && gaps && (
            <div className="mt-3">
              <GapsPanel gaps={gaps} />
            </div>
          )}

          {canExpand && !expanded && (
            <button
              type="button"
              onClick={() => setExpanded(true)}
              className="mt-3 text-xs text-blue-400 hover:text-blue-300 inline-flex items-center gap-1"
            >
              ▸ Show full match analysis (per-skill confidence & gaps)
            </button>
          )}
        </div>
        {job.url && (
          <a
            href={job.url}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 rounded-lg bg-blue-600 px-4 py-2 text-xs font-semibold text-white hover:bg-blue-500 hover:scale-[1.02] shadow shadow-blue-950/50 transition-all"
          >
            {job.is_deep_link ? "Search ↗" : "Apply →"}
          </a>
        )}
      </div>
    </div>
  );
}

function ExternalSearchSection({
  links, keywords, location, onRefresh,
}: {
  links: ExternalSearchLink[];
  keywords: string;
  location: string;
  onRefresh: () => void;
}) {
  // The prop is consumed inside JSX below; placeholder so TS doesn't flag it.
  if (links.length === 0) return null;
  return (
    <div className="rounded-xl border border-slate-700/40 bg-slate-800/20 p-5">
      <div className="mb-3 flex items-start justify-between gap-2 flex-wrap">
        <div>
          <h3 className="text-sm font-semibold text-slate-200">🔍 Search on External Platforms</h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Opens in browser with your current inputs pre-filled
            {keywords ? (
              <> · <span className="font-mono text-blue-400">{keywords}</span></>
            ) : null}
            {location ? (
              <> · <span className="text-slate-300">📍 {location}</span></>
            ) : null}
          </p>
        </div>
        <button
          type="button"
          onClick={onRefresh}
          className="text-xs text-blue-400 hover:text-blue-300"
          title="Refresh external links from current Job Title / Location inputs"
        >
          ↻ Refresh links
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {links.map((l) => (
          <a
            key={l.portal}
            href={l.url}
            target="_blank"
            rel="noopener noreferrer"
            className="rounded-lg bg-slate-700/60 border border-slate-600/40 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-700 hover:border-slate-500 transition-all inline-flex items-center gap-1.5"
          >
            <span>{l.icon}</span> {l.label} ↗
          </a>
        ))}
      </div>
    </div>
  );
}

function ResumeKeywordPanel({ profileId }: { profileId: number }) {
  const [keywords, setKeywords] = useState<ResumeKeyword[]>([]);
  const [total, setTotal] = useState(0);
  const [topTerms, setTopTerms] = useState<string[]>([]);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    fetchResumeKeywords(profileId)
      .then((r) => {
        setKeywords(r.keywords);
        setTotal(r.total);
        setTopTerms(r.top_terms);
      })
      .catch(() => {});
  }, [profileId]);

  if (total === 0) return null;

  const display = showAll ? keywords : keywords.slice(0, 20);
  const maxWeight = Math.max(...keywords.map((k) => k.weight), 1);

  return (
    <div className="rounded-xl border border-slate-700/40 bg-slate-800/20 p-5">
      <div className="flex items-center justify-between mb-3">
        <div>
          <h3 className="text-sm font-semibold text-slate-200">🔑 Your Resume Keyword Profile</h3>
          <p className="text-xs text-slate-400 mt-0.5">
            {total} keywords extracted · Top: {topTerms.join(", ")}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowAll((s) => !s)}
          className="text-xs text-blue-400 hover:text-blue-300"
        >
          {showAll ? "Show less" : `Show all ${total}`}
        </button>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {display.map((kw) => {
          const intensity = kw.weight / maxWeight;
          const bg = intensity >= 0.7
            ? "bg-blue-600/30 text-blue-200 border-blue-500/30"
            : intensity >= 0.4
              ? "bg-slate-700/60 text-slate-300 border-slate-600/40"
              : "bg-slate-800 text-slate-400 border-slate-700/40";
          return (
            <span
              key={kw.canonical}
              className={`rounded-full px-2.5 py-0.5 text-xs font-medium border ${bg}`}
              title={`Weight: ${kw.weight.toFixed(2)} · Source: ${kw.source}`}
            >
              {kw.term}
            </span>
          );
        })}
      </div>
    </div>
  );
}

export default function JobsTab({ profileId, profile }: Props) {
  const { toast } = useToast();
  // Load persisted state for this profile once, on mount. This gives each
  // profile its own independent search state that survives tab switches,
  // browser refreshes, and even full reloads.
  const persistedRef = useRef<Partial<PersistedState> | null>(null);
  if (persistedRef.current === null && typeof window !== "undefined") {
    persistedRef.current = loadPersisted(profileId);
  }
  const p = (key: keyof PersistedState, fallback: any) =>
    persistedRef.current && persistedRef.current[key] !== undefined
      ? (persistedRef.current[key] as any)
      : fallback;

  const [loading, setLoading] = useState(false);
  const [jobs, setJobs] = useState<JobMatch[]>(p("jobs", []));
  const [total, setTotal] = useState<number>(p("total", 0));
  const [hasMore, setHasMore] = useState<boolean>(p("hasMore", false));
  const [error, setError] = useState("");
  const [searched, setSearched] = useState<boolean>(p("searched", false));
  const [queryEcho, setQueryEcho] = useState<string>(p("queryEcho", ""));
  const [externalLinks, setExternalLinks] = useState<ExternalSearchLink[]>(p("externalLinks", []));
  const [externalKeywords, setExternalKeywords] = useState<string>(p("externalKeywords", ""));
  const [, setExternalLocation] = useState<string>(p("externalLocation", ""));

  // Filters — initial values come from persisted state, falling back to
  // the profile defaults so first-time users get sensible defaults.
  const defaultRole = (() => {
    const roles = profile?.experience?.map((e) => e.role).filter(Boolean) || [];
    return roles[0] || "";
  })();
  const [jobTitle, setJobTitle] = useState<string>(p("jobTitle", defaultRole));
  const [location, setLocation] = useState<string>(p("location", profile?.location || ""));
  const [portal, setPortal] = useState<string>(p("portal", "all"));
  const [showAdvanced, setShowAdvanced] = useState<boolean>(p("showAdvanced", false));
  const [minYears, setMinYears] = useState<number>(p("minYears", 0));
  const [maxYears, setMaxYears] = useState<number>(p("maxYears", 50));
  const [datePosted, setDatePosted] = useState<"any" | "last_24h" | "last_7d" | "last_30d">(
    p("datePosted", "any") as "any" | "last_24h" | "last_7d" | "last_30d"
  );
  const [minMatchScore, setMinMatchScore] = useState<number>(p("minMatchScore", 50));
  const [jobTypeChips, setJobTypeChips] = useState<string[]>(p("jobTypeChips", []));
  const [minSalary, setMinSalary] = useState<number>(p("minSalary", 0));
  const [maxSalary, setMaxSalary] = useState<number>(p("maxSalary", 0));
  const [salaryCurrency, setSalaryCurrency] = useState<string>(p("salaryCurrency", "USD"));
  const [experienceLevel, setExperienceLevel] = useState<string>(p("experienceLevel", ""));
  const [workTypeFilter, setWorkTypeFilter] = useState<string>(p("workTypeFilter", ""));
  const [industryChips, setIndustryChips] = useState<string[]>(p("industryChips", []));
  const [sort, setSort] = useState<"best_match" | "recent" | "salary" | "location">(
    p("sort", "best_match") as "best_match" | "recent" | "salary" | "location"
  );
  const [limit] = useState(20);
  const [offset, setOffset] = useState(0);

  // Saved filters
  const [savedFilters, setSavedFilters] = useState<SavedFilter[]>([]);
  const [showSaveDialog, setShowSaveDialog] = useState(false);
  const [newFilterName, setNewFilterName] = useState("");
  const [editingFilterId, setEditingFilterId] = useState<number | null>(null);
  const [editingFilterName, setEditingFilterName] = useState("");

  // Persist state on every change so navigating away and back keeps
  // the user's exact search context.
  useEffect(() => {
    savePersisted(profileId, {
      jobTitle, location, portal, minYears, maxYears, datePosted,
      minMatchScore, jobTypeChips, minSalary, maxSalary, salaryCurrency,
      experienceLevel, workTypeFilter, industryChips,
      sort, jobs, total, hasMore, queryEcho, searched,
      externalLinks, externalKeywords, externalLocation: location,
      showAdvanced,
    });
  }, [
    profileId, jobTitle, location, portal, minYears, maxYears, datePosted,
    minMatchScore, jobTypeChips, minSalary, maxSalary, salaryCurrency,
    experienceLevel, workTypeFilter, industryChips,
    sort, jobs, total, hasMore, queryEcho, searched,
    externalLinks, externalKeywords, showAdvanced,
  ]);

  // Load saved filters on mount
  useEffect(() => {
    listSavedFilters(profileId).then(setSavedFilters).catch(() => {});
  }, [profileId]);

  // Refresh external search links whenever the current inputs change so the
  // "Search on External Platforms" section reflects the live Job Title /
  // Location values, not a cached profile snapshot. We debounce so we don't
  // hit the backend on every keystroke. All advanced filters (experience
  // level, work type, time posted, salary + currency) are forwarded so
  // each external site opens with the same filter the user applied.
  const externalRefreshTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  function scheduleExternalRefresh(delay = 350) {
    if (externalRefreshTimer.current) clearTimeout(externalRefreshTimer.current);
    externalRefreshTimer.current = setTimeout(() => {
      getExternalSearchLinks(
        profileId,
        jobTitle,
        location,
        experienceLevel,
        jobTypeChips.length > 0 ? jobTypeChips[0] : workTypeFilter,
        datePosted,
        minSalary,
        salaryCurrency,
      )
        .then((r) => {
          setExternalLinks(r.links);
          setExternalKeywords(r.keywords);
          setExternalLocation(r.location);
        })
        .catch(() => {});
    }, delay);
  }
  useEffect(() => {
    scheduleExternalRefresh();
    return () => {
      if (externalRefreshTimer.current) clearTimeout(externalRefreshTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobTitle, location, profileId]);
  function refreshExternalLinksNow() {
    scheduleExternalRefresh(0);
  }

  function currentOptions(): JobSearchOptions {
    return {
      limit,
      offset,
      jobTitle,
      location,
      portal,
      minYears,
      maxYears,
      datePosted,
      minMatchScore,
      jobType: jobTypeChips.join(","),
      minSalary,
      maxSalary,
      industries: industryChips.join(","),
      sort,
    };
  }

  function applyOptions(o: Partial<JobSearchOptions>) {
    if (o.minYears !== undefined) setMinYears(o.minYears);
    if (o.maxYears !== undefined) setMaxYears(o.maxYears);
    if (o.datePosted !== undefined) setDatePosted(o.datePosted);
    if (o.minMatchScore !== undefined) setMinMatchScore(o.minMatchScore);
    if (o.jobType !== undefined) setJobTypeChips(o.jobType ? o.jobType.split(",") : []);
    if (o.minSalary !== undefined) setMinSalary(o.minSalary);
    if (o.maxSalary !== undefined) setMaxSalary(o.maxSalary);
    if (o.industries !== undefined) setIndustryChips(o.industries ? o.industries.split(",") : []);
    if (o.sort !== undefined) setSort(o.sort as "best_match" | "recent" | "salary" | "location");
  }

  async function search(append = false) {
    setLoading(true);
    setError("");
    try {
      const opts = currentOptions();
      if (append) opts.offset = offset;
      const r = await searchJobs(profileId, opts);
      setQueryEcho(r.query);
      setTotal(r.total);
      setHasMore(r.has_more);
      setJobs(append ? [...jobs, ...r.jobs] : r.jobs);
      setOffset(append ? offset + r.limit : r.limit);
      setSearched(true);
      if (!append) {
        toast("success", "Jobs found", `${r.total} positions found`);
      }
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Job search failed";
      setError(msg);
      toast("error", "Job search failed", msg);
    } finally {
      setLoading(false);
    }
  }

  async function searchAiRecommended() {
    setMinMatchScore(80);
    setLoading(true);
    setError("");
    try {
      const opts = { ...currentOptions(), minMatchScore: 80, offset: 0 };
      const r = await searchJobs(profileId, opts);
      setQueryEcho(r.query);
      setTotal(r.total);
      setHasMore(r.has_more);
      setJobs(r.jobs);
      setOffset(r.limit);
      setSearched(true);
      if (r.total === 0) {
        toast("info", "No 80%+ matches", "Try adding more skills to your profile or lower the threshold");
      } else {
        toast("success", "AI Recommended Jobs", "Showing your top matches at 80%+ fit");
      }
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Job search failed";
      setError(msg);
      toast("error", "Job search failed", msg);
    } finally {
      setLoading(false);
    }
  }

  function applySavedFilter(sf: SavedFilter) {
    applyOptions(sf.filters as Partial<JobSearchOptions>);
    if (sf.sort) setSort(sf.sort as "best_match" | "recent" | "salary" | "location");
    setTimeout(() => search(), 0);
    toast("info", "Filter applied", sf.name);
  }

  function resetFilters() {
    setJobTitle(defaultRole);
    setLocation(profile?.location || "");
    setPortal("all");
    setMinYears(0);
    setMaxYears(50);
    setDatePosted("any");
    setMinMatchScore(50);
    setJobTypeChips([]);
    setMinSalary(0);
    setMaxSalary(0);
    setSalaryCurrency("USD");
    setExperienceLevel("");
    setWorkTypeFilter("");
    setIndustryChips([]);
    setSort("best_match");
    setJobs([]);
    setTotal(0);
    setHasMore(false);
    setQueryEcho("");
    setSearched(false);
    setOffset(0);
    setError("");
    if (typeof window !== "undefined") {
      try { window.localStorage.removeItem(STORAGE_KEY(profileId)); } catch {}
    }
    toast("info", "Filters reset", "All inputs cleared for this profile");
  }

  async function handleSaveFilter() {
    if (!newFilterName.trim()) return;
    try {
      const sf = await createSavedFilter(
        profileId,
        newFilterName.trim(),
        {
          min_years: minYears,
          max_years: maxYears,
          date_posted: datePosted,
          min_match_score: minMatchScore,
          job_type: jobTypeChips.join(","),
          min_salary: minSalary,
          max_salary: maxSalary,
          industries: industryChips.join(","),
        },
        sort,
      );
      setSavedFilters([sf, ...savedFilters]);
      setNewFilterName("");
      setShowSaveDialog(false);
      toast("success", "Filter saved", sf.name);
    } catch {
      toast("error", "Save failed", "Could not save filter preset");
    }
  }

  async function handleDeleteFilter(sfId: number) {
    try {
      await deleteSavedFilter(profileId, sfId);
      setSavedFilters(savedFilters.filter((f) => f.id !== sfId));
      toast("success", "Filter deleted", "");
    } catch {
      toast("error", "Delete failed", "Could not delete filter preset");
    }
  }

  function startEditFilterName(sf: SavedFilter) {
    setEditingFilterId(sf.id);
    setEditingFilterName(sf.name);
  }

  async function commitEditFilterName(sf: SavedFilter) {
    const newName = editingFilterName.trim();
    if (!newName || newName === sf.name) {
      setEditingFilterId(null);
      return;
    }
    try {
      const updated = await updateSavedFilter(profileId, sf.id, { name: newName });
      setSavedFilters(savedFilters.map((f) => (f.id === sf.id ? updated : f)));
      toast("success", "Filter renamed", newName);
    } catch {
      toast("error", "Rename failed", "Could not rename filter preset");
    } finally {
      setEditingFilterId(null);
    }
  }

  function toggleChip(arr: string[], value: string, setter: (v: string[]) => void) {
    setter(arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value]);
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">Live Job Matching</h2>
          <p className="text-sm text-slate-400 mt-1">
            Advanced 9-factor AI matching across 10+ boards — semantic skill embeddings, TF-IDF, fuzzy matching & per-skill gap analysis.
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowAdvanced((s) => !s)}
            className="rounded-lg border border-slate-600 bg-slate-800 px-3 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700 transition-all"
          >
            {showAdvanced ? "Hide" : "Show"} Advanced
          </button>
          <button
            type="button"
            onClick={resetFilters}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm font-medium text-slate-300 hover:bg-slate-700 transition-all"
            title="Clear all inputs and search results for this profile"
          >
            ↺ Reset
          </button>
          <button
            type="button"
            onClick={searchAiRecommended}
            disabled={loading}
            className="rounded-lg bg-gradient-to-r from-purple-600 to-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:scale-[1.02] shadow-md shadow-purple-950/50 active:scale-[0.98] disabled:opacity-50 transition-all"
          >
            ✨ AI Recommended Top Jobs
          </button>
          <button
            onClick={() => search(false)}
            disabled={loading}
            className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 shadow-md shadow-blue-950/50 hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 transition-all"
          >
            {loading ? "Searching…" : "Find Jobs"}
          </button>
        </div>
      </div>

      {/* Top row — basic filters */}
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
            <option value="linkedin">LinkedIn (deep-link)</option>
            <option value="indeed">Indeed (deep-link)</option>
            <option value="glassdoor">Glassdoor (deep-link)</option>
            <option value="google_jobs">Google Jobs (deep-link)</option>
            <option value="adzuna">Adzuna (API)</option>
            <option value="remotive">Remotive</option>
            <option value="remoteok">RemoteOK</option>
            <option value="arbeitnow">Arbeitnow</option>
            <option value="himalayas">Himalayas</option>
            <option value="themuse">The Muse</option>
            <option value="jobicy">Jobicy</option>
            <option value="weworkremotely">We Work Remotely</option>
            <option value="findwork">Findwork</option>
            <option value="jooble">Jooble</option>
            <option value="reed">Reed (UK)</option>
            <option value="usajobs">USAJOBS</option>
          </select>
        </div>
      </div>

      {/* Advanced filter panel (collapsible) */}
      {showAdvanced && (
        <div className="border border-slate-700/40 bg-slate-800/20 p-5 rounded-2xl space-y-4">
          <h3 className="text-sm font-semibold text-slate-200">Advanced Filters</h3>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* Years of experience */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Years of Experience</label>
              <div className="flex gap-2 items-center">
                <input
                  type="number"
                  min={0}
                  max={50}
                  value={minYears}
                  onChange={(e) => setMinYears(parseInt(e.target.value || "0"))}
                  className="w-20 rounded-lg bg-slate-900 border border-slate-700 px-2 py-1.5 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                />
                <span className="text-slate-500">–</span>
                <input
                  type="number"
                  min={0}
                  max={50}
                  value={maxYears}
                  onChange={(e) => setMaxYears(parseInt(e.target.value || "50"))}
                  className="w-20 rounded-lg bg-slate-900 border border-slate-700 px-2 py-1.5 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                />
              </div>
            </div>

            {/* Date posted */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Date Posted</label>
              <select
                value={datePosted}
                onChange={(e) => setDatePosted(e.target.value as "any" | "last_24h" | "last_7d" | "last_30d")}
                className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-1.5 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
              >
                <option value="any">Any time</option>
                <option value="last_24h">Last 24 hours</option>
                <option value="last_7d">Last 7 days</option>
                <option value="last_30d">Last 30 days</option>
              </select>
            </div>

            {/* Match score slider */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                Min Match Score: <span className="text-blue-400 tabular-nums">{minMatchScore}%</span>
              </label>
              <input
                type="range"
                min={0}
                max={100}
                value={minMatchScore}
                onChange={(e) => setMinMatchScore(parseInt(e.target.value))}
                className="w-full"
              />
            </div>

            {/* Salary range + currency */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Salary Range</label>
              <div className="flex gap-2 items-center flex-wrap">
                <input
                  type="number"
                  min={0}
                  value={minSalary || ""}
                  onChange={(e) => setMinSalary(parseInt(e.target.value || "0"))}
                  placeholder="min"
                  className="w-24 rounded-lg bg-slate-900 border border-slate-700 px-2 py-1.5 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                />
                <span className="text-slate-500">–</span>
                <input
                  type="number"
                  min={0}
                  value={maxSalary || ""}
                  onChange={(e) => setMaxSalary(parseInt(e.target.value || "0"))}
                  placeholder="max"
                  className="w-24 rounded-lg bg-slate-900 border border-slate-700 px-2 py-1.5 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                />
                <input
                  type="text"
                  value={salaryCurrency}
                  onChange={(e) => setSalaryCurrency(e.target.value.toUpperCase().slice(0, 3))}
                  placeholder="USD"
                  maxLength={3}
                  title="3-letter currency code (USD, INR, GBP, EUR, CAD, AUD, SGD, JPY)"
                  className="w-16 rounded-lg bg-slate-900 border border-slate-700 px-2 py-1.5 text-sm text-slate-200 text-center uppercase focus:border-blue-500 focus:outline-none"
                />
                <span className="text-xs text-slate-500">currency</span>
              </div>
            </div>

            {/* Experience level (for external links) */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Experience Level (external links)</label>
              <select
                value={experienceLevel}
                onChange={(e) => setExperienceLevel(e.target.value)}
                className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-1.5 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
              >
                <option value="">Any</option>
                <option value="internship">Internship</option>
                <option value="entry">Entry level</option>
                <option value="associate">Associate</option>
                <option value="mid-senior">Mid-Senior</option>
                <option value="director">Director</option>
                <option value="executive">Executive</option>
              </select>
            </div>

            {/* Work type filter (for external links) */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Work Type (external links)</label>
              <select
                value={workTypeFilter}
                onChange={(e) => setWorkTypeFilter(e.target.value)}
                className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-1.5 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
              >
                <option value="">Any</option>
                <option value="full-time">On-site</option>
                <option value="remote">Remote</option>
                <option value="hybrid">Hybrid</option>
              </select>
            </div>

            {/* Sort */}
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1.5">Sort By</label>
              <select
                value={sort}
                onChange={(e) => setSort(e.target.value as "best_match" | "recent" | "salary" | "location")}
                className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-1.5 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
              >
                <option value="best_match">Best Match</option>
                <option value="recent">Most Recent</option>
                <option value="salary">Highest Salary</option>
                <option value="location">Closest Location</option>
              </select>
            </div>
          </div>

          {/* Job type chips */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Job Type</label>
            <div className="flex flex-wrap gap-1.5">
              {JOB_TYPES.map((t) => {
                const on = jobTypeChips.includes(t);
                return (
                  <button
                    key={t}
                    type="button"
                    onClick={() => toggleChip(jobTypeChips, t, setJobTypeChips)}
                    className={`rounded-full px-3 py-1 text-xs font-medium border transition-all ${
                      on
                        ? "bg-blue-600/30 border-blue-500 text-blue-200"
                        : "bg-slate-800 border-slate-700 text-slate-300 hover:border-slate-500"
                    }`}
                  >
                    {t}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Industry chips */}
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1.5">Industry</label>
            <div className="flex flex-wrap gap-1.5">
              {INDUSTRY_CHOICES.map((t) => {
                const on = industryChips.includes(t);
                return (
                  <button
                    key={t}
                    type="button"
                    onClick={() => toggleChip(industryChips, t, setIndustryChips)}
                    className={`rounded-full px-3 py-1 text-xs font-medium border transition-all ${
                      on
                        ? "bg-emerald-600/30 border-emerald-500 text-emerald-200"
                        : "bg-slate-800 border-slate-700 text-slate-300 hover:border-slate-500"
                    }`}
                  >
                    {t}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Saved filters row */}
          <div className="border-t border-slate-700/40 pt-3">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs font-semibold text-slate-300">Saved Filters:</span>
                {savedFilters.length === 0 ? (
                  <span className="text-xs text-slate-500">None</span>
                ) : (
                  savedFilters.map((sf) => (
                    <div key={sf.id} className="flex items-center gap-1 bg-slate-800 border border-slate-700 rounded-full pl-3 pr-1 py-0.5">
                      {editingFilterId === sf.id ? (
                        <input
                          autoFocus
                          value={editingFilterName}
                          onChange={(e) => setEditingFilterName(e.target.value)}
                          onBlur={() => commitEditFilterName(sf)}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") commitEditFilterName(sf);
                            if (e.key === "Escape") setEditingFilterId(null);
                          }}
                          className="bg-transparent text-xs text-slate-100 outline-none w-32"
                        />
                      ) : (
                        <button
                          type="button"
                          onClick={() => applySavedFilter(sf)}
                          className="text-xs text-blue-300 hover:text-blue-200"
                          title="Apply this filter preset"
                        >
                          {sf.name}
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => startEditFilterName(sf)}
                        className="text-slate-500 hover:text-blue-300 text-xs"
                        title="Rename saved filter"
                      >
                        ✎
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDeleteFilter(sf.id)}
                        className="text-slate-500 hover:text-red-400 text-sm leading-none"
                        title="Delete saved filter"
                      >
                        ×
                      </button>
                    </div>
                  ))
                )}
              </div>
              <button
                type="button"
                onClick={() => setShowSaveDialog((s) => !s)}
                className="text-xs text-blue-400 hover:text-blue-300"
              >
                💾 Save current filters
              </button>
            </div>
            {showSaveDialog && (
              <div className="mt-2 flex gap-2 items-center">
                <input
                  type="text"
                  value={newFilterName}
                  onChange={(e) => setNewFilterName(e.target.value)}
                  placeholder="Filter name (e.g. Senior Remote Python)"
                  className="flex-1 rounded-lg bg-slate-900 border border-slate-700 px-3 py-1.5 text-sm text-slate-200 placeholder-slate-600 focus:border-blue-500 focus:outline-none"
                />
                <button
                  type="button"
                  onClick={handleSaveFilter}
                  className="rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-500"
                >
                  Save
                </button>
                <button
                  type="button"
                  onClick={() => setShowSaveDialog(false)}
                  className="text-xs text-slate-400 hover:text-slate-200"
                >
                  Cancel
                </button>
              </div>
            )}
          </div>
        </div>
      )}

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

      {queryEcho && searched && (
        <p className="text-xs text-slate-400">
          Search query: <span className="font-mono bg-slate-800 border border-slate-700 px-2 py-0.5 rounded text-blue-400">{queryEcho}</span>
          {total > 0 && (
            <span className="ml-3 text-slate-500">Showing {jobs.length} of {total}</span>
          )}
        </p>
      )}

      {searched && jobs.length === 0 && !loading && (
        <div className="rounded-xl bg-amber-500/10 border border-amber-500/20 p-4 text-sm text-amber-300">
          No jobs found. Try relaxing the filters (lower min_match_score, broader date range) or check your profile skills.
        </div>
      )}

      <ExternalSearchSection
        links={externalLinks}
        keywords={externalKeywords}
        location={location}
        onRefresh={refreshExternalLinksNow}
      />

      <ResumeKeywordPanel profileId={profileId} />

      <div className="space-y-3">
        {jobs.map((job) => (
          <JobCard key={job.id} job={job} />
        ))}
      </div>

      {hasMore && !loading && (
        <div className="flex justify-center pt-2">
          <button
            type="button"
            onClick={() => search(true)}
            className="rounded-lg border border-slate-600 bg-slate-800 px-4 py-2 text-sm font-medium text-slate-200 hover:bg-slate-700 transition-all"
          >
            Load more jobs
          </button>
        </div>
      )}
    </div>
  );
}
