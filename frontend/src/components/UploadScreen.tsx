import { useState, useRef } from "react";
import type { DragEvent } from "react";
import type { AuthUser } from "../types";
import { importFile, listProfiles, deleteProfile } from "../api";

interface Props {
  onImported: (profileId: number, warnings: string[]) => void;
  authUser?: AuthUser | null;
  onLogout?: () => void;
}

const ACCEPTED = [".json", ".csv", ".xml", ".docx", ".doc", ".pdf", ".tex"];

const FEATURES = [
  { icon: "🤖", title: "AI Analysis", desc: "ATS score, strengths, keyword gaps" },
  { icon: "✍️", title: "Cover Letters", desc: "AI-generated per job & company" },
  { icon: "🗺️", title: "Career Roadmap", desc: "1–10 year growth & portfolio plans" },
  { icon: "🔍", title: "Job Matching", desc: "Live search with skill-overlap scores" },
  { icon: "📤", title: "7 Export Formats", desc: "JSON · CSV · XML · DOCX · PDF · LaTeX · HTML" },
  { icon: "🏠", title: "100% Local", desc: "No cloud, no subscription, data stays yours" },
];

export default function UploadScreen({ onImported, authUser, onLogout }: Props) {
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [profiles, setProfiles] = useState<{ id: number; full_name: string; email: string }[] | null>(null);
  const [loadingProfiles, setLoadingProfiles] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setError(null);
    setLoading(true);
    try {
      const result = await importFile(file);
      onImported(result.profile_id, result.warnings);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
        ?? "Upload failed — check backend is running on port 8000.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  async function loadProfiles() {
    setLoadingProfiles(true);
    try {
      const list = await listProfiles();
      setProfiles(list);
    } finally {
      setLoadingProfiles(false);
    }
  }

  async function handleDeleteProfile(id: number) {
    if (!confirm("Delete this profile?")) return;
    await deleteProfile(id);
    setProfiles((prev) => prev?.filter((p) => p.id !== id) ?? null);
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-950 to-slate-900 flex flex-col">
      {/* Top nav */}
      <header className="flex items-center justify-between px-8 py-5">
        <div className="flex items-center gap-3">
          <span className="text-3xl">🎓</span>
          <div>
            <h1 className="text-white font-bold text-xl leading-tight">AI Career Studio</h1>
            <p className="text-blue-300 text-xs">AI-Powered Career Platform</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={profiles ? () => setProfiles(null) : loadProfiles}
            disabled={loadingProfiles}
            className="rounded-xl border border-blue-500/40 bg-blue-500/10 px-4 py-2 text-sm text-blue-300 hover:bg-blue-500/20 transition-colors disabled:opacity-50"
          >
            {loadingProfiles ? "Loading…" : profiles ? "← Back" : "📂 Open Saved Profile"}
          </button>
          {authUser ? (
            <div className="flex items-center gap-2">
              <span className="text-blue-300 text-sm hidden sm:block">{authUser.username}</span>
              <button
                onClick={onLogout}
                className="rounded-xl border border-slate-600 px-3 py-2 text-xs text-slate-400 hover:bg-slate-700/60 hover:text-slate-200 transition-colors"
              >
                Sign Out
              </button>
            </div>
          ) : onLogout && (
            <button
              onClick={onLogout}
              className="rounded-xl border border-slate-600 px-3 py-2 text-xs text-slate-400 hover:bg-slate-700/60 hover:text-slate-200 transition-colors"
            >
              Sign In
            </button>
          )}
        </div>
      </header>

      <div className="flex-1 flex flex-col items-center justify-center px-6 py-8 gap-10">

        {/* Saved profiles list */}
        {profiles !== null ? (
          <div className="w-full max-w-2xl">
            <h2 className="text-white text-xl font-semibold mb-4">Saved Profiles</h2>
            {profiles.length === 0 ? (
              <div className="rounded-2xl border border-white/10 bg-white/5 p-8 text-center text-slate-400">
                No saved profiles yet. Upload a resume to get started.
              </div>
            ) : (
              <div className="space-y-3">
                {profiles.map((p) => (
                  <div
                    key={p.id}
                    className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-5 py-4 hover:bg-white/10 transition-colors"
                  >
                    <div>
                      <p className="text-white font-semibold">{p.full_name}</p>
                      <p className="text-slate-400 text-sm">{p.email} · Profile #{p.id}</p>
                    </div>
                    <div className="flex gap-3">
                      <button
                        onClick={() => onImported(p.id, [])}
                        className="rounded-xl bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-500"
                      >
                        Open →
                      </button>
                      <button
                        onClick={() => handleDeleteProfile(p.id)}
                        className="rounded-xl border border-red-500/40 px-3 py-2 text-sm text-red-400 hover:bg-red-500/10"
                      >
                        🗑
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <>
            {/* Hero + upload */}
            <div className="text-center space-y-3 max-w-xl">
              <h2 className="text-4xl font-bold text-white">
                Your Resume,{" "}
                <span className="bg-gradient-to-r from-blue-400 to-teal-400 bg-clip-text text-transparent">
                  Supercharged
                </span>
              </h2>
              <p className="text-slate-400 text-lg">
                Upload any resume format and get an AI-powered career profile with analysis, cover letters, roadmaps, and live job matching — all running locally.
              </p>
            </div>

            {/* Drop zone */}
            <div
              onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
              onDragLeave={() => setDragging(false)}
              onDrop={onDrop}
              onClick={() => inputRef.current?.click()}
              className={`
                w-full max-w-xl cursor-pointer rounded-3xl border-2 border-dashed p-14 text-center
                transition-all duration-200
                ${dragging
                  ? "border-blue-400 bg-blue-500/10 scale-[1.02]"
                  : "border-white/20 bg-white/5 hover:border-blue-400/60 hover:bg-white/8"}
              `}
            >
              <div className="text-6xl mb-4">{loading ? "⏳" : "📄"}</div>
              {loading ? (
                <p className="text-blue-300 text-lg font-semibold animate-pulse">Parsing your resume…</p>
              ) : (
                <>
                  <p className="text-white text-lg font-semibold mb-1">
                    Drag &amp; drop your resume here
                  </p>
                  <p className="text-slate-400 text-sm mb-4">or click to browse files</p>
                  <div className="flex flex-wrap justify-center gap-2">
                    {ACCEPTED.map((ext) => (
                      <span key={ext} className="rounded-full bg-blue-500/20 px-3 py-1 text-xs font-mono text-blue-300">
                        {ext}
                      </span>
                    ))}
                  </div>
                </>
              )}
              <input
                ref={inputRef}
                type="file"
                accept={ACCEPTED.join(",")}
                className="hidden"
                onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }}
              />
            </div>

            {error && (
              <div className="w-full max-w-xl rounded-2xl border border-red-500/40 bg-red-500/10 p-4 text-sm text-red-300">
                ⚠️ {error}
              </div>
            )}

            {/* Feature grid */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 w-full max-w-2xl">
              {FEATURES.map(({ icon, title, desc }) => (
                <div
                  key={title}
                  className="rounded-2xl border border-white/10 bg-white/5 p-4 hover:bg-white/8 transition-colors"
                >
                  <div className="text-2xl mb-2">{icon}</div>
                  <p className="text-white text-sm font-semibold">{title}</p>
                  <p className="text-slate-400 text-xs mt-0.5">{desc}</p>
                </div>
              ))}
            </div>
          </>
        )}
      </div>

      {/* Footer */}
      <footer className="text-center py-4 text-xs text-slate-600">
        Built with ❤️ by <span className="text-slate-500">Haseeb Mir</span> · Powered by{" "}
        <span className="text-slate-500">Claude Code</span>
      </footer>
    </div>
  );
}
