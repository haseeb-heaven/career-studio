import { useState } from "react";
import { analyzeProfile } from "../../api";
import type { AnalysisResult } from "../../api";

interface Props { profileId: number; }

function ScoreRing({ score }: { score: number }) {
  const color = score >= 80 ? "text-green-600" : score >= 60 ? "text-yellow-600" : "text-red-500";
  return (
    <div className={`flex flex-col items-center justify-center w-32 h-32 rounded-full border-8 ${
      score >= 80 ? "border-green-400" : score >= 60 ? "border-yellow-400" : "border-red-400"
    } bg-white`}>
      <span className={`text-4xl font-bold ${color}`}>{score}</span>
      <span className="text-xs text-slate-500">/ 100</span>
    </div>
  );
}

export default function AnalysisTab({ profileId }: Props) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState("");

  async function run() {
    setLoading(true);
    setError("");
    try {
      const r = await analyzeProfile(profileId);
      setResult(r);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Analysis failed";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-slate-800">AI Resume Analysis</h2>
          <p className="text-sm text-slate-500">Get an ATS score, strengths, weaknesses, and actionable suggestions.</p>
        </div>
        <button
          onClick={run}
          disabled={loading}
          className="rounded-lg bg-blue-700 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50"
        >
          {loading ? "Analyzing…" : "Analyze Resume"}
        </button>
      </div>

      {error && <div className="rounded-lg bg-red-50 border border-red-200 p-4 text-sm text-red-700">{error}</div>}

      {loading && (
        <div className="flex items-center gap-3 text-sm text-blue-600 animate-pulse">
          <span className="text-2xl">🤖</span> AI is reviewing your resume…
        </div>
      )}

      {result && (
        <div className="space-y-6">
          <div className="flex items-center gap-8">
            <ScoreRing score={result.score} />
            <div>
              <p className="text-2xl font-bold text-slate-800">
                {result.score >= 80 ? "Excellent!" : result.score >= 60 ? "Good — room to improve" : "Needs work"}
              </p>
              <p className="text-sm text-slate-500 mt-1">ATS compatibility score</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="rounded-xl border border-green-200 bg-green-50 p-4">
              <h3 className="font-semibold text-green-800 mb-2">✅ Strengths</h3>
              <ul className="space-y-1">
                {result.strengths.map((s, i) => (
                  <li key={i} className="text-sm text-green-700">• {s}</li>
                ))}
              </ul>
            </div>
            <div className="rounded-xl border border-red-200 bg-red-50 p-4">
              <h3 className="font-semibold text-red-800 mb-2">⚠️ Weaknesses</h3>
              <ul className="space-y-1">
                {result.weaknesses.map((s, i) => (
                  <li key={i} className="text-sm text-red-700">• {s}</li>
                ))}
              </ul>
            </div>
          </div>

          <div className="rounded-xl border border-blue-200 bg-blue-50 p-4">
            <h3 className="font-semibold text-blue-800 mb-2">💡 Suggestions</h3>
            <ol className="space-y-2">
              {result.suggestions.map((s, i) => (
                <li key={i} className="text-sm text-blue-800 flex gap-2">
                  <span className="font-bold text-blue-400">{i + 1}.</span> {s}
                </li>
              ))}
            </ol>
          </div>

          <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
            <h3 className="font-semibold text-slate-700 mb-2">🏷️ ATS Keywords to Add</h3>
            <div className="flex flex-wrap gap-2">
              {result.ats_keywords.map((kw, i) => (
                <span key={i} className="rounded-full bg-white border border-slate-300 px-3 py-1 text-xs font-medium text-slate-600">
                  {kw}
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
