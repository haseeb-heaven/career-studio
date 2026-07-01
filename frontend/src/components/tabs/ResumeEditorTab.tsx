import { useState, useEffect, useRef } from "react";
import {
  generateResumeDraft, listResumeDrafts, saveResumeDraft, deleteResumeDraft,
  suggestResumeEdits, exportResumeDraftBlob,
} from "../../api";
import type { ResumeDraft } from "../../api";
import { useToast } from "../Toast";

interface Props { profileId: number; }

const STORAGE_KEY = (profileId: number) => `resumeEditorTab.state.v1.${profileId}`;

interface PersistedState {
  activeDraftId: number | null;
  title: string;
  content: string;
}

function loadPersisted(profileId: number): Partial<PersistedState> | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY(profileId));
    return raw ? (JSON.parse(raw) as Partial<PersistedState>) : null;
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

const EXPORT_FORMATS = [
  { fmt: "txt",  label: "TXT" },
  { fmt: "md",   label: "Markdown" },
  { fmt: "docx", label: "DOCX" },
  { fmt: "pdf",  label: "PDF" },
] as const;

export default function ResumeEditorTab({ profileId }: Props) {
  const { toast } = useToast();

  const persistedRef = useRef<Partial<PersistedState> | null>(null);
  if (persistedRef.current === null && typeof window !== "undefined") {
    persistedRef.current = loadPersisted(profileId);
  }
  const p = <K extends keyof PersistedState>(key: K, fallback: PersistedState[K]) =>
    persistedRef.current && persistedRef.current[key] !== undefined
      ? (persistedRef.current[key] as PersistedState[K])
      : fallback;

  const [drafts, setDrafts] = useState<ResumeDraft[]>([]);
  const [loadingDrafts, setLoadingDrafts] = useState(true);
  const [activeDraftId, setActiveDraftId] = useState<number | null>(p("activeDraftId", null));
  const [title, setTitle] = useState(p("title", ""));
  const [content, setContent] = useState(p("content", ""));
  const [generating, setGenerating] = useState(false);
  const [saving, setSaving] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    listResumeDrafts(profileId)
      .then((rows) => {
        setDrafts(rows);
        // Only fall back to the most recent draft if nothing was restored
        // from localStorage and no draft is currently open.
        if (activeDraftId === null && rows.length > 0) {
          setActiveDraftId(rows[0].id);
          setTitle(rows[0].title);
          setContent(rows[0].content);
        }
      })
      .finally(() => setLoadingDrafts(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [profileId]);

  // Persist the editor's in-progress state so navigating away and back
  // (or refreshing) keeps the open draft and any unsaved edits.
  useEffect(() => {
    savePersisted(profileId, { activeDraftId, title, content });
  }, [profileId, activeDraftId, title, content]);

  // Debounced autosave to the backend while the user types, so the draft
  // in history stays in sync without a manual "Save" click.
  const autosaveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  useEffect(() => {
    if (activeDraftId === null) return;
    setSaving(true);
    if (autosaveTimer.current) clearTimeout(autosaveTimer.current);
    autosaveTimer.current = setTimeout(() => {
      saveResumeDraft(profileId, activeDraftId, content, title)
        .then((d) => {
          setDrafts((ds) => ds.map((x) => (x.id === d.id ? d : x)));
        })
        .catch(() => {})
        .finally(() => setSaving(false));
    }, 1000);
    return () => {
      if (autosaveTimer.current) clearTimeout(autosaveTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [content, title]);

  async function generate() {
    setGenerating(true);
    setError("");
    setSuggestions([]);
    try {
      const d = await generateResumeDraft(profileId, `Draft ${drafts.length + 1}`);
      setDrafts((ds) => [d, ...ds]);
      setActiveDraftId(d.id);
      setTitle(d.title);
      setContent(d.content);
      toast("success", "Draft generated", "AI seeded a resume draft from your profile");
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Generation failed";
      setError(msg);
      toast("error", "Draft generation failed", msg);
    } finally {
      setGenerating(false);
    }
  }

  function openDraft(d: ResumeDraft) {
    setActiveDraftId(d.id);
    setTitle(d.title);
    setContent(d.content);
    setSuggestions([]);
    setError("");
  }

  async function remove(draftId: number) {
    await deleteResumeDraft(profileId, draftId);
    setDrafts((ds) => ds.filter((d) => d.id !== draftId));
    if (activeDraftId === draftId) {
      setActiveDraftId(null);
      setTitle("");
      setContent("");
      setSuggestions([]);
    }
  }

  async function getSuggestions() {
    if (activeDraftId === null) return;
    setLoadingSuggestions(true);
    setError("");
    try {
      const s = await suggestResumeEdits(profileId, activeDraftId);
      setSuggestions(s);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail ?? "Suggestion request failed";
      setError(msg);
      toast("error", "AI suggestions failed", msg);
    } finally {
      setLoadingSuggestions(false);
    }
  }

  async function download(fmt: string) {
    if (activeDraftId === null) return;
    try {
      const blob = await exportResumeDraftBlob(profileId, activeDraftId, fmt);
      const cleanName = title.replace(/[^\w\-]/g, "_").replace(/^_+|_+$/g, "") || "resume";
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${cleanName}.${fmt}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast("error", "Export failed", "Could not export the draft");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-lg font-semibold text-white">Live Resume Editor</h2>
          <p className="text-sm text-slate-400 mt-1">
            Edit your resume as plain text, get AI suggestions, and export when you're happy with it.
          </p>
        </div>
        <button
          onClick={generate}
          disabled={generating}
          className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-500 disabled:opacity-50 transition-all shrink-0"
        >
          {generating ? "Generating…" : activeDraftId === null ? "Generate from Profile" : "Generate New Draft"}
        </button>
      </div>

      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 p-4 text-sm text-red-300">
          <p className="font-semibold mb-1">❌ Error</p>
          <p className="text-red-400/80">{error}</p>
          {error.includes("API key") && (
            <p className="mt-2 text-xs text-slate-400">→ Configure your API key in the <strong>Settings</strong> tab.</p>
          )}
        </div>
      )}

      {generating && (
        <div className="flex items-center gap-3 text-sm text-blue-400 animate-pulse">
          <span className="text-xl">🤖</span> AI is drafting your resume…
        </div>
      )}

      {activeDraftId === null && !generating ? (
        <div className="rounded-xl border border-dashed border-slate-700/60 bg-slate-800/20 p-6 text-center">
          <p className="text-sm text-slate-300">No draft open yet.</p>
          <p className="text-xs text-slate-500 mt-1">
            Click <span className="text-slate-300 font-semibold">Generate from Profile</span> to seed a draft from your existing profile data.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2 space-y-3">
            <div className="flex items-center gap-3">
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="flex-1 rounded-lg bg-slate-900 border border-slate-700 px-3 py-1.5 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                placeholder="Draft title"
              />
              <span className="text-xs text-slate-500 shrink-0">{saving ? "Saving…" : "Saved"}</span>
            </div>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={24}
              spellCheck={false}
              className="w-full rounded-lg bg-slate-900 border border-slate-700 px-4 py-3 text-sm text-slate-200 font-mono leading-relaxed focus:border-blue-500 focus:outline-none resize-y"
              placeholder="# Your Name&#10;&#10;## Summary&#10;..."
            />
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={getSuggestions}
                disabled={loadingSuggestions}
                className="rounded-lg bg-purple-700 px-4 py-2 text-xs font-semibold text-white hover:bg-purple-600 disabled:opacity-50 transition-all"
              >
                {loadingSuggestions ? "Thinking…" : "✨ Get AI Suggestions"}
              </button>
              {EXPORT_FORMATS.map(({ fmt, label }) => (
                <button
                  key={fmt}
                  onClick={() => download(fmt)}
                  className="rounded-lg border border-slate-700 px-3 py-2 text-xs font-semibold text-slate-300 hover:border-blue-500 hover:text-blue-400 transition-all"
                >
                  ⬇ {label}
                </button>
              ))}
            </div>

            {suggestions.length > 0 && (
              <div className="rounded-xl border border-purple-500/20 bg-purple-950/10 p-4 space-y-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-purple-300">AI Suggestions</h3>
                <ul className="space-y-1.5">
                  {suggestions.map((s, i) => (
                    <li key={i} className="text-sm text-purple-200 flex items-start gap-2">
                      <span className="text-purple-400 shrink-0">✦</span>
                      <span>{s}</span>
                    </li>
                  ))}
                </ul>
                <p className="text-[11px] text-slate-500">Review and apply the ones you like directly in the editor.</p>
              </div>
            )}
          </div>

          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-slate-400">Drafts</h3>
            {loadingDrafts ? (
              <p className="text-xs text-slate-500">Loading…</p>
            ) : drafts.length === 0 ? (
              <p className="text-xs text-slate-500">No drafts yet.</p>
            ) : (
              <div className="space-y-2">
                {drafts.map((d) => (
                  <div
                    key={d.id}
                    className={`rounded-xl border p-3 transition-colors ${
                      d.id === activeDraftId ? "border-blue-500 bg-blue-950/20" : "border-slate-700/40 bg-slate-800/20 hover:border-slate-600"
                    }`}
                  >
                    <p className="text-sm font-semibold text-slate-200 truncate">{d.title}</p>
                    {d.updated_at && (
                      <p className="text-[11px] text-slate-500 mt-0.5">{new Date(d.updated_at).toLocaleString()}</p>
                    )}
                    <div className="flex gap-3 mt-2">
                      <button onClick={() => openDraft(d)} className="text-xs text-blue-400 font-semibold hover:text-blue-300">Open</button>
                      <button onClick={() => remove(d.id)} className="text-xs text-red-400 font-semibold hover:text-red-300">Delete</button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
