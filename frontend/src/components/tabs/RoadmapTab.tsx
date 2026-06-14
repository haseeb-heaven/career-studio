import { useState, useEffect } from "react";
import { generateRoadmap, listRoadmaps, deleteRoadmap } from "../../api";
import type { RoadmapResult } from "../../api";

interface Props { profileId: number; }

const PLAN_TYPES = [
  { value: "roadmap",   label: "Career Roadmap",      emoji: "🗺️" },
  { value: "growth",    label: "Growth Plan",         emoji: "📈" },
  { value: "portfolio", label: "Portfolio Strategy",  emoji: "🎨" },
] as const;

export default function RoadmapTab({ profileId }: Props) {
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

  async function generate() {
    setGenerating(true);
    setError("");
    try {
      const r = await generateRoadmap(profileId, planType, targetRole, years);
      setCurrent(r);
      setHistory((h) => [{ ...r, created_at: new Date().toISOString() }, ...h]);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Generation failed";
      setError(msg);
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
      <h2 className="text-lg font-semibold text-slate-800">Career Roadmap & Growth Plan</h2>

      <div className="flex gap-2 flex-wrap">
        {PLAN_TYPES.map(({ value, label, emoji }) => (
          <button
            key={value}
            onClick={() => setPlanType(value)}
            className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
              planType === value
                ? "bg-blue-700 text-white border-blue-700"
                : "bg-white text-slate-600 border-slate-300 hover:border-blue-400"
            }`}
          >
            {emoji} {label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Target Role</label>
          <input
            type="text"
            value={targetRole}
            onChange={(e) => setTargetRole(e.target.value)}
            placeholder="e.g. Principal Engineer, CTO, ML Lead…"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Years Horizon: {years}</label>
          <input
            type="range"
            min={1}
            max={10}
            value={years}
            onChange={(e) => setYears(Number(e.target.value))}
            className="w-full"
          />
          <div className="flex justify-between text-xs text-slate-400 mt-1">
            <span>1 year</span><span>5 years</span><span>10 years</span>
          </div>
        </div>
      </div>

      {error && <div className="rounded-lg bg-red-50 border border-red-200 p-3 text-sm text-red-700">{error}</div>}

      <button
        onClick={generate}
        disabled={generating}
        className="rounded-lg bg-blue-700 px-6 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50"
      >
        {generating ? "Generating…" : "Generate Plan"}
      </button>

      {generating && (
        <p className="text-sm text-blue-600 animate-pulse">🤖 AI is building your roadmap…</p>
      )}

      {current && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-5 space-y-2">
          <h3 className="font-semibold text-blue-900 capitalize">
            {PLAN_TYPES.find((t) => t.value === current.plan_type)?.emoji}{" "}
            {PLAN_TYPES.find((t) => t.value === current.plan_type)?.label}
          </h3>
          <pre className="whitespace-pre-wrap text-sm text-slate-700 font-sans leading-relaxed">
            {current.content}
          </pre>
        </div>
      )}

      {!loadingHistory && history.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-slate-700">History</h3>
          {history.map((plan) => (
            <div key={plan.id} className="rounded-lg border border-slate-200 bg-white p-4 flex items-center justify-between">
              <div>
                <span className="text-sm font-medium text-slate-800 capitalize">
                  {PLAN_TYPES.find((t) => t.value === plan.plan_type)?.emoji}{" "}
                  {PLAN_TYPES.find((t) => t.value === plan.plan_type)?.label}
                </span>
                {plan.created_at && (
                  <p className="text-xs text-slate-400">{new Date(plan.created_at).toLocaleString()}</p>
                )}
              </div>
              <div className="flex gap-3">
                <button onClick={() => setCurrent(plan)} className="text-xs text-blue-600 underline hover:text-blue-800">View</button>
                <button onClick={() => remove(plan.id)} className="text-xs text-red-500 underline hover:text-red-700">Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
