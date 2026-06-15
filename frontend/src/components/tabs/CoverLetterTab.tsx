import { useState, useEffect } from "react";
import { generateCoverLetter, listCoverLetters, deleteCoverLetter } from "../../api";
import type { CoverLetterResult } from "../../api";
import { useToast } from "../Toast";

interface Props { profileId: number; }

export default function CoverLetterTab({ profileId }: Props) {
  const { toast } = useToast();
  const [jobTitle, setJobTitle] = useState("");
  const [company, setCompany] = useState("");
  const [notes, setNotes] = useState("");
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");
  const [current, setCurrent] = useState<CoverLetterResult | null>(null);
  const [history, setHistory] = useState<CoverLetterResult[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);

  useEffect(() => {
    listCoverLetters(profileId)
      .then(setHistory)
      .finally(() => setLoadingHistory(false));
  }, [profileId]);

  async function generate() {
    if (!jobTitle.trim() || !company.trim()) {
      setError("Job title and company are required.");
      return;
    }
    setGenerating(true);
    setError("");
    try {
      const r = await generateCoverLetter(profileId, jobTitle, company, notes);
      setCurrent(r);
      setHistory((h) => [{ ...r, created_at: new Date().toISOString() }, ...h]);
      toast("success", "Cover letter generated", `For ${jobTitle} at ${company}`);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Generation failed";
      setError(msg);
      toast("error", "Cover letter failed", msg);
    } finally {
      setGenerating(false);
    }
  }

  async function remove(clId: number) {
    await deleteCoverLetter(profileId, clId);
    setHistory((h) => h.filter((x) => x.id !== clId));
    if (current?.id === clId) setCurrent(null);
  }

  function copyToClipboard(text: string) {
    navigator.clipboard.writeText(text);
  }

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-slate-800">Cover Letter Generator</h2>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Job Title *</label>
          <input
            type="text"
            value={jobTitle}
            onChange={(e) => setJobTitle(e.target.value)}
            placeholder="e.g. Senior Software Engineer"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Company *</label>
          <input
            type="text"
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="e.g. Acme Corp"
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div className="sm:col-span-2">
          <label className="block text-sm font-medium text-slate-700 mb-1">Extra notes (optional)</label>
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Anything specific to highlight or mention…"
            rows={2}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300">
          <p className="font-semibold mb-0.5">❌ Generation Error</p>
          <p className="text-red-400/80">{error}</p>
          {error.includes("API key") && <p className="mt-1.5 text-xs text-slate-400">→ Configure your API key in <strong>Settings</strong>.</p>}
        </div>
      )}

      <button
        onClick={generate}
        disabled={generating}
        className="rounded-lg bg-blue-700 px-6 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50"
      >
        {generating ? "Generating…" : "Generate Cover Letter"}
      </button>

      {generating && (
        <p className="text-sm text-blue-600 animate-pulse">✍️ AI is writing your cover letter…</p>
      )}

      {current && (
        <div className="rounded-xl border border-blue-200 bg-blue-50 p-5 space-y-3">
          <div className="flex items-center justify-between">
            <h3 className="font-semibold text-blue-900">
              {current.job_title} @ {current.company}
            </h3>
            <button
              onClick={() => copyToClipboard(current.content)}
              className="text-xs text-blue-600 underline hover:text-blue-800"
            >
              Copy to Clipboard
            </button>
          </div>
          <pre className="whitespace-pre-wrap text-sm text-slate-700 font-sans leading-relaxed">
            {current.content}
          </pre>
        </div>
      )}

      {!loadingHistory && history.length > 0 && (
        <div className="space-y-3">
          <h3 className="text-sm font-semibold text-slate-700">History</h3>
          {history.map((cl) => (
            <div key={cl.id} className="rounded-lg border border-slate-200 bg-white p-4 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-800">
                  {cl.job_title} @ {cl.company}
                </span>
                <div className="flex gap-3">
                  <button
                    onClick={() => setCurrent(cl)}
                    className="text-xs text-blue-600 underline hover:text-blue-800"
                  >
                    View
                  </button>
                  <button
                    onClick={() => remove(cl.id)}
                    className="text-xs text-red-500 underline hover:text-red-700"
                  >
                    Delete
                  </button>
                </div>
              </div>
              {cl.created_at && (
                <p className="text-xs text-slate-400">{new Date(cl.created_at).toLocaleString()}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
