import { useState, useEffect, useMemo } from "react";
import { generateRoadmap, listRoadmaps, deleteRoadmap } from "../../api";
import type { RoadmapResult } from "../../api";
import { useToast } from "../Toast";

interface Props { profileId: number; }

const PLAN_TYPES = [
  { value: "roadmap",   label: "Career Roadmap",      emoji: "🗺️" },
  { value: "growth",    label: "Growth Plan",         emoji: "📈" },
  { value: "portfolio", label: "Portfolio Strategy",  emoji: "🎨" },
] as const;

function safeExternalUrl(raw?: string): string {
  try {
    const u = new URL(raw ?? "");
    return u.protocol === "http:" || u.protocol === "https:" ? u.toString() : "";
  } catch {
    return "";
  }
}

/**
 * Try to extract a JSON object from AI text. AI responses often wrap JSON
 * in ```json ... ``` fences, or have a leading sentence before the JSON.
 * Returns the parsed object or null when no JSON can be located.
 */
function extractJsonObject(raw: string): any {
  const text = (raw ?? "").trim();
  if (!text) return null;
  // Direct parse
  try {
    const direct = JSON.parse(text);
    if (direct && typeof direct === "object") return direct;
  } catch {}
  // Strip ```json ... ``` fences
  const fence = text.match(/```(?:json)?\s*([\s\S]*?)\s*```/i);
  if (fence) {
    try {
      const inside = JSON.parse(fence[1].trim());
      if (inside && typeof inside === "object") return inside;
    } catch {}
  }
  // Find the first { ... last } substring and parse it
  const first = text.indexOf("{");
  const last = text.lastIndexOf("}");
  if (first !== -1 && last !== -1 && last > first) {
    try {
      const obj = JSON.parse(text.slice(first, last + 1));
      if (obj && typeof obj === "object") return obj;
    } catch {}
  }
  return null;
}

interface VisualPlanProps {
  plan: RoadmapResult;
  emoji: string;
  label: string;
}

function VisualPlan({ plan, emoji, label }: VisualPlanProps) {
  const data = extractJsonObject(plan.content);

  if (!data) {
    return (
      <div className="rounded-xl border border-slate-700/60 bg-slate-800/30 p-5 space-y-3">
        <h3 className="font-semibold text-white capitalize flex items-center gap-2">
          <span>{emoji}</span> <span>{label}</span>
        </h3>
        <pre className="whitespace-pre-wrap text-sm text-slate-300 font-sans leading-relaxed bg-slate-900/40 p-4 rounded-lg border border-slate-800/60">
          {plan.content}
        </pre>
      </div>
    );
  }

  const timeline: any[] = Array.isArray(data.timeline) ? data.timeline : [];
  const projects: any[] = Array.isArray(data.projects) ? data.projects : [];
  const learningResources: any[] = Array.isArray(data.learning_resources) ? data.learning_resources : [];

  return (
    <div className="space-y-6">
      {/* Overview Card */}
      <div className="rounded-2xl bg-gradient-to-br from-blue-900/30 via-indigo-950/20 to-slate-900 border border-blue-500/20 p-6 shadow-lg shadow-slate-950/50">
        <div className="flex items-center gap-3 mb-2">
          <span className="text-3xl">{emoji}</span>
          <h3 className="text-lg font-bold text-white leading-tight">{data.title || label}</h3>
        </div>
        {data.overview && (
          <p className="text-sm text-slate-300 leading-relaxed mt-2">{data.overview}</p>
        )}
      </div>

      {/* Timeline Section */}
      {timeline.length > 0 && (
        <div className="space-y-4">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <span>📅</span> Timeline & Milestones
          </h4>
          <div className="relative border-l border-slate-750 ml-4 pl-6 space-y-6">
            {timeline.map((item: any, idx: number) => (
              <div key={idx} className="relative">
                {/* Timeline Dot */}
                <div className="absolute -left-[32px] top-1.5 w-4 h-4 rounded-full bg-blue-500 border-4 border-slate-900 shadow shadow-blue-500/40" />
                <div className="rounded-xl border border-slate-700/40 bg-slate-850 p-5 space-y-3 hover:border-slate-600 transition-colors">
                  <h5 className="font-bold text-white text-sm">{item.period || `Period ${idx + 1}`}</h5>
                  
                  {/* Milestones list */}
                  {Array.isArray(item.milestones) && item.milestones.length > 0 && (
                    <div className="space-y-1.5">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Key Milestones:</p>
                      <ul className="grid grid-cols-1 sm:grid-cols-2 gap-1.5">
                        {item.milestones.map((m: string, i: number) => (
                          <li key={i} className="text-xs text-slate-200 flex items-start gap-1.5">
                            <span className="text-green-400 shrink-0">✓</span>
                            <span>{m}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {/* Skills tags */}
                  {Array.isArray(item.skills) && item.skills.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 items-center pt-1">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mr-1">Skills:</span>
                      {item.skills.map((s: string, i: number) => (
                        <span key={i} className="rounded bg-green-500/10 text-green-400 border border-green-500/20 px-2 py-0.5 text-[10px] font-semibold">
                          {s}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Certifications tags */}
                  {Array.isArray(item.certifications) && item.certifications.length > 0 && (
                    <div className="flex flex-wrap gap-1.5 items-center">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mr-1">Certs:</span>
                      {item.certifications.map((c: string, i: number) => (
                        <span key={i} className="rounded bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 text-[10px] font-semibold">
                          {c}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Actions list */}
                  {Array.isArray(item.actions) && item.actions.length > 0 && (
                    <div className="space-y-1.5 pt-1">
                      <p className="text-[10px] font-bold uppercase tracking-wider text-slate-500">Recommended Actions:</p>
                      <ul className="space-y-1">
                        {item.actions.map((act: string, i: number) => (
                          <li key={i} className="text-xs text-slate-300 flex items-start gap-1.5">
                            <span className="text-blue-400 shrink-0">✦</span>
                            <span>{act}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Projects Section */}
      {projects.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <span>🚀</span> Showcase Projects to Build
          </h4>
          <div className="grid grid-cols-1 gap-3.5">
            {projects.map((proj: any, idx: number) => (
              <div key={idx} className="rounded-xl border border-slate-700/40 bg-slate-800/20 p-5 space-y-3">
                <div className="flex items-center gap-2 justify-between flex-wrap">
                  <h5 className="font-bold text-white text-sm flex items-center gap-1.5">
                    <span>🛠️</span> {proj.name}
                  </h5>
                  {Array.isArray(proj.tech_stack) && proj.tech_stack.length > 0 && (
                    <div className="flex flex-wrap gap-1">
                      {proj.tech_stack.map((t: string, i: number) => (
                        <span key={i} className="rounded bg-slate-800 text-slate-300 border border-slate-700 px-2 py-0.5 text-[10px] font-semibold">
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
                <p className="text-xs text-slate-300 leading-relaxed">{proj.description}</p>
                {proj.github_strategy && (
                  <div className="rounded-lg bg-slate-900/50 border border-slate-800/80 p-3 text-xs">
                    <p className="text-slate-400 font-semibold mb-1 flex items-center gap-1">
                      <span>📁</span> GitHub Presentation:
                    </p>
                    <p className="text-slate-300 leading-relaxed">{proj.github_strategy}</p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Learning Resources Section */}
      {learningResources.length > 0 && (
        <div className="space-y-3">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 flex items-center gap-2">
            <span>📚</span> Learning Resources & Video Courses
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {learningResources.map((res: any, idx: number) => {
              const isYouTube = res.platform?.toLowerCase().includes("youtube") || res.url?.includes("youtube.com");
              const cardBorder = isYouTube ? "border-red-500/20 bg-red-950/5" : "border-blue-500/20 bg-blue-950/5";
              const labelColor = isYouTube ? "text-red-400 bg-red-500/5 border-red-500/10" : "text-blue-400 bg-blue-500/5 border-blue-500/10";
              const btnStyle = isYouTube ? "bg-red-700/80 hover:bg-red-650 hover:scale-[1.01]" : "bg-blue-700/80 hover:bg-blue-650 hover:scale-[1.01]";
              const icon = isYouTube ? "▶️" : "🎓";
              
              return (
                <div key={idx} className={`rounded-xl border ${cardBorder} p-5 flex flex-col justify-between space-y-4 hover:bg-slate-800/10 transition-colors`}>
                  <div className="space-y-2.5">
                    <div>
                      <span className={`inline-flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-wider ${labelColor} border px-2 py-0.5 rounded`}>
                        <span>{icon}</span> <span>{res.platform}</span>
                      </span>
                    </div>
                    <h5 className="font-bold text-slate-100 text-sm leading-snug">{res.title}</h5>
                    <p className="text-xs text-slate-300 leading-relaxed">{res.description}</p>
                  </div>
                  {safeExternalUrl(res.url) && (
                    <a
                      href={safeExternalUrl(res.url)}
                      target="_blank"
                      rel="noopener noreferrer"
                      className={`w-full text-center rounded-lg ${btnStyle} py-2 text-xs font-semibold text-white shadow shadow-slate-950/40 transition-all block`}
                    >
                      {isYouTube ? "Search YouTube Tutorial" : "Go to Course"}
                    </a>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Additional Strategy */}
      {data.additional_strategy && (
        <div className="rounded-xl border border-slate-700/40 bg-slate-800/30 p-5 space-y-2">
          <h4 className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center gap-1.5">
            <span>📈</span> Additional Strategy
          </h4>
          <p className="text-xs text-slate-300 leading-relaxed font-sans">{data.additional_strategy}</p>
        </div>
      )}
    </div>
  );
}

export default function RoadmapTab({ profileId }: Props) {
  const { toast } = useToast();
  const [planType, setPlanType] = useState("roadmap");
  const [targetRole, setTargetRole] = useState("");
  const [years, setYears] = useState(3);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [current, setCurrent] = useState<RoadmapResult | null>(null);
  const [history, setHistory] = useState<RoadmapResult[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);

  useEffect(() => {
    listRoadmaps(profileId)
      .then(setHistory)
      .finally(() => setLoadingHistory(false));
  }, [profileId]);

  // History and current view are filtered by the selected plan type so
  // switching tabs shows the right plan immediately (no stale display).
  const filteredHistory = useMemo(
    () => history.filter((p) => p.plan_type === planType),
    [history, planType],
  );
  const currentForType = current && current.plan_type === planType ? current : null;

  function handleTabChange(next: string) {
    if (next === planType) return;
    setPlanType(next);
    setError("");
    // Pick the most recent plan of the new type from history so the UI
    // immediately shows the right thing instead of the stale plan.
    const nextMostRecent = history.find((p) => p.plan_type === next);
    setCurrent(nextMostRecent ?? null);
  }

  async function generate() {
    setGenerating(true);
    setError("");
    try {
      const r = await generateRoadmap(profileId, planType, targetRole, years);
      setCurrent(r);
      setHistory((h) => [{ ...r, created_at: new Date().toISOString() }, ...h]);
      toast("success", "Plan generated", `${years}-year ${planType} plan created`);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Generation failed";
      setError(msg);
      toast("error", "Plan generation failed", msg);
    } finally {
      setGenerating(false);
    }
  }

  async function remove(planId: number) {
    await deleteRoadmap(profileId, planId);
    setHistory((h) => h.filter((x) => x.id !== planId));
    if (current?.id === planId) setCurrent(null);
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-white font-sans">Career Roadmap & Growth Plan</h2>
        <p className="text-sm text-slate-400 mt-1">Generate a step-by-step roadmap, learning growth path, or portfolio project plan tailored to your target role.</p>
      </div>

      <div className="flex gap-2 flex-wrap">
        {PLAN_TYPES.map(({ value, label, emoji }) => (
          <button
            key={value}
            onClick={() => handleTabChange(value)}
            className={`px-4 py-2 rounded-lg text-sm font-semibold border transition-all ${
              planType === value
                ? "bg-blue-600 text-white border-blue-500 shadow-md shadow-blue-950/45"
                : "bg-slate-800/40 text-slate-400 border-slate-700/65 hover:border-slate-500 hover:text-slate-200"
            }`}
          >
            <span className="mr-1">{emoji}</span> {label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5">Target Role</label>
          <input
            type="text"
            value={targetRole}
            onChange={(e) => setTargetRole(e.target.value)}
            placeholder="e.g. Principal Engineer, CTO, ML Lead…"
            className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1.5">Years Horizon: {years}</label>
          <input
            type="range"
            min={1}
            max={10}
            value={years}
            onChange={(e) => setYears(Number(e.target.value))}
            className="w-full accent-blue-500"
          />
          <div className="flex justify-between text-[11px] text-slate-500 mt-1">
            <span>1 year</span><span>5 years</span><span>10 years</span>
          </div>
        </div>
      </div>

      {error && (
        <div className="rounded-xl bg-red-500/10 border border-red-500/20 p-4 text-sm text-red-300">
          <span className="font-semibold block mb-1">❌ Generation failed</span>
          <p>{error}</p>
        </div>
      )}

      <button
        onClick={generate}
        disabled={generating}
        className="rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-blue-500 hover:scale-[1.01] shadow-md shadow-blue-950/50 disabled:opacity-50 transition-all"
      >
        {generating ? "Generating…" : "Generate Plan"}
      </button>

      {generating && (
        <div className="flex items-center gap-3 text-sm text-blue-400 animate-pulse">
          <span className="text-xl">🤖</span> AI is building your career plan…
        </div>
      )}

      {currentForType ? (
        <VisualPlan
          plan={currentForType}
          emoji={PLAN_TYPES.find((t) => t.value === currentForType.plan_type)?.emoji || "🧭"}
          label={PLAN_TYPES.find((t) => t.value === currentForType.plan_type)?.label || "Plan"}
        />
      ) : !generating && (
        <div className="rounded-xl border border-dashed border-slate-700/60 bg-slate-800/20 p-6 text-center">
          <p className="text-sm text-slate-300">
            No <span className="text-blue-400 font-semibold">{PLAN_TYPES.find((t) => t.value === planType)?.label}</span> yet.
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Set the target role + years horizon above and click <span className="text-slate-300 font-semibold">Generate Plan</span>.
          </p>
        </div>
      )}

      {!loadingHistory && filteredHistory.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-slate-400">
            Previous {PLAN_TYPES.find((t) => t.value === planType)?.label} Plans
          </h3>
          <div className="space-y-2">
            {filteredHistory.map((plan) => (
              <div key={plan.id} className="rounded-xl border border-slate-700/40 bg-slate-800/20 p-4 flex items-center justify-between hover:border-slate-600 transition-colors">
                <div>
                  <span className="text-sm font-semibold text-slate-200 capitalize flex items-center gap-1.5">
                    <span>{PLAN_TYPES.find((t) => t.value === plan.plan_type)?.emoji}</span>
                    <span>{PLAN_TYPES.find((t) => t.value === plan.plan_type)?.label}</span>
                  </span>
                  {plan.created_at && (
                    <p className="text-[11px] text-slate-500 mt-0.5">{new Date(plan.created_at).toLocaleString()}</p>
                  )}
                </div>
                <div className="flex gap-4">
                  <button onClick={() => setCurrent(plan)} className="text-xs text-blue-400 font-semibold hover:text-blue-300 transition-colors">View</button>
                  <button onClick={() => remove(plan.id)} className="text-xs text-red-400 font-semibold hover:text-red-300 transition-colors">Delete</button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
