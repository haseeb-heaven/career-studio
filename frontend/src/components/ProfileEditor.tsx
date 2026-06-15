import { useState, useEffect } from "react";
import type { Profile } from "../types";
import { getProfile } from "../api";
import ContactTab from "./tabs/ContactTab";
import SummaryTab from "./tabs/SummaryTab";
import SkillsTab from "./tabs/SkillsTab";
import ExperienceTab from "./tabs/ExperienceTab";
import ProjectsTab from "./tabs/ProjectsTab";
import EducationTab from "./tabs/EducationTab";
import CertificationsTab from "./tabs/CertificationsTab";
import ExportPanel from "./ExportPanel";
import AnalysisTab from "./tabs/AnalysisTab";
import CoverLetterTab from "./tabs/CoverLetterTab";
import RoadmapTab from "./tabs/RoadmapTab";
import JobsTab from "./tabs/JobsTab";
import LogsTab from "./tabs/LogsTab";
import SettingsTab from "./tabs/SettingsTab";

type TabName =
  | "Contact" | "Summary" | "Skills" | "Experience" | "Projects" | "Education" | "Certifications"
  | "Analysis" | "Cover Letter" | "Roadmap" | "Jobs"
  | "Export"
  | "Logs" | "Settings";

interface NavItem {
  id: TabName;
  icon: string;
  label: string;
}

interface NavGroup {
  title: string;
  items: NavItem[];
}

const NAV_GROUPS: NavGroup[] = [
  {
    title: "Profile",
    items: [
      { id: "Contact",        icon: "👤", label: "Contact" },
      { id: "Summary",        icon: "📝", label: "Summary" },
      { id: "Skills",         icon: "⚡", label: "Skills" },
      { id: "Experience",     icon: "💼", label: "Experience" },
      { id: "Projects",       icon: "🚀", label: "Projects" },
      { id: "Education",      icon: "🎓", label: "Education" },
      { id: "Certifications", icon: "🏅", label: "Certifications" },
    ],
  },
  {
    title: "AI Tools",
    items: [
      { id: "Analysis",     icon: "📊", label: "Analysis" },
      { id: "Cover Letter", icon: "✍️",  label: "Cover Letter" },
      { id: "Roadmap",      icon: "🗺️", label: "Roadmap" },
      { id: "Jobs",         icon: "🔍", label: "Job Matching" },
    ],
  },
  {
    title: "Export",
    items: [
      { id: "Export", icon: "📤", label: "Export" },
    ],
  },
  {
    title: "System",
    items: [
      { id: "Logs",     icon: "📋", label: "Activity Logs" },
      { id: "Settings", icon: "⚙️", label: "Settings" },
    ],
  },
];

interface Props {
  profileId: number;
  importWarnings?: string[];
  onBack: () => void;
}

export default function ProfileEditor({ profileId, importWarnings = [], onBack }: Props) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [activeTab, setActiveTab] = useState<TabName>("Contact");
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [warningsDismissed, setWarningsDismissed] = useState(false);

  useEffect(() => {
    setLoading(true);
    getProfile(profileId)
      .then(setProfile)
      .finally(() => setLoading(false));
  }, [profileId]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-900">
        <div className="text-center space-y-3">
          <div className="text-5xl animate-pulse">🎓</div>
          <p className="text-blue-400 font-medium">Loading profile…</p>
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-900">
        <p className="text-red-400">Failed to load profile #{profileId}</p>
      </div>
    );
  }

  function handleSectionUpdate(patch: Partial<Profile>) {
    setProfile((prev) => prev ? { ...prev, ...patch } : prev);
  }

  function renderTab() {
    if (!profile) return null;
    switch (activeTab) {
      case "Contact":        return <ContactTab profile={profile} onChange={setProfile} />;
      case "Summary":        return <SummaryTab profile={profile} onChange={setProfile} />;
      case "Skills":         return <SkillsTab profile={profile} onUpdate={handleSectionUpdate} />;
      case "Experience":     return <ExperienceTab profile={profile} onUpdate={handleSectionUpdate} />;
      case "Projects":       return <ProjectsTab profile={profile} onUpdate={handleSectionUpdate} />;
      case "Education":      return <EducationTab profile={profile} onUpdate={handleSectionUpdate} />;
      case "Certifications": return <CertificationsTab profile={profile} onUpdate={handleSectionUpdate} />;
      case "Export":         return <ExportPanel profileId={profile.id} fullName={profile.full_name} />;
      case "Analysis":       return <AnalysisTab profileId={profile.id} />;
      case "Cover Letter":   return <CoverLetterTab profileId={profile.id} />;
      case "Roadmap":        return <RoadmapTab profileId={profile.id} />;
      case "Jobs":           return <JobsTab profileId={profile.id} />;
      case "Logs":           return <LogsTab />;
      case "Settings":       return <SettingsTab />;
    }
  }

  const activeItem = NAV_GROUPS.flatMap((g) => g.items).find((i) => i.id === activeTab);

  return (
    <div className="flex h-screen bg-slate-900 overflow-hidden">
      {/* ── Left Sidebar ── */}
      <aside
        className={`
          flex flex-col bg-slate-800 border-r border-slate-700/60 transition-all duration-200 shrink-0
          ${sidebarOpen ? "w-56" : "w-14"}
        `}
      >
        {/* Sidebar header */}
        <div className="flex items-center gap-3 px-3 py-4 border-b border-slate-700/60">
          <span className="text-2xl shrink-0">🎓</span>
          {sidebarOpen && (
            <div className="min-w-0">
              <p className="text-white font-bold text-sm leading-tight truncate">AI Career Studio</p>
              <p className="text-slate-400 text-xs truncate">{profile.full_name}</p>
            </div>
          )}
          <button
            onClick={() => setSidebarOpen((o) => !o)}
            className="ml-auto shrink-0 text-slate-500 hover:text-slate-300 transition-colors"
          >
            {sidebarOpen ? "◀" : "▶"}
          </button>
        </div>

        {/* Nav groups */}
        <nav className="flex-1 overflow-y-auto py-3 space-y-5 px-2">
          {NAV_GROUPS.map((group) => (
            <div key={group.title}>
              {sidebarOpen && (
                <p className="text-xs font-bold text-slate-500 uppercase tracking-widest px-2 mb-1.5">
                  {group.title}
                </p>
              )}
              {!sidebarOpen && <div className="border-t border-slate-700/40 my-2" />}
              <div className="space-y-0.5">
                {group.items.map((item) => {
                  const isActive = activeTab === item.id;
                  return (
                    <button
                      key={item.id}
                      onClick={() => setActiveTab(item.id)}
                      title={!sidebarOpen ? item.label : undefined}
                      className={`
                        w-full flex items-center gap-3 rounded-lg px-2 py-2 text-sm transition-all
                        ${isActive
                          ? "bg-blue-600 text-white shadow-sm shadow-blue-900/50"
                          : "text-slate-400 hover:bg-slate-700/60 hover:text-slate-200"}
                      `}
                    >
                      <span className="text-base shrink-0">{item.icon}</span>
                      {sidebarOpen && (
                        <span className="truncate font-medium">{item.label}</span>
                      )}
                      {sidebarOpen && isActive && (
                        <span className="ml-auto w-1.5 h-1.5 rounded-full bg-white/60 shrink-0" />
                      )}
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </nav>

        {/* Import warnings in sidebar */}
        {sidebarOpen && importWarnings.length > 0 && !warningsDismissed && (
          <div className="mx-2 mb-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-3">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-xs font-bold text-amber-400 uppercase tracking-wide">⚠ Import Notes</span>
              <button onClick={() => setWarningsDismissed(true)} className="text-slate-500 hover:text-slate-300 text-sm leading-none">×</button>
            </div>
            <ul className="space-y-1">
              {importWarnings.map((w, i) => (
                <li key={i} className="text-xs text-amber-300/80 leading-relaxed">• {w}</li>
              ))}
            </ul>
          </div>
        )}

        {/* Sidebar footer */}
        <div className="p-2 border-t border-slate-700/60 space-y-1">
          <div className={`flex items-center gap-2 px-2 py-1.5 ${sidebarOpen ? "" : "justify-center"}`}>
            <span className="text-slate-500 text-xs shrink-0">#{profileId}</span>
            {sidebarOpen && (
              <span className="text-slate-500 text-xs truncate">{profile.email}</span>
            )}
          </div>
          <button
            onClick={onBack}
            title={!sidebarOpen ? "Upload new resume" : undefined}
            className="w-full flex items-center gap-2 rounded-lg px-2 py-2 text-sm text-slate-400 hover:bg-slate-700/60 hover:text-slate-200 transition-all"
          >
            <span className="shrink-0">⬆️</span>
            {sidebarOpen && <span className="font-medium">Upload New</span>}
          </button>
        </div>
      </aside>

      {/* ── Main Content ── */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Top bar */}
        <header className="flex items-center gap-4 border-b border-slate-700/60 bg-slate-800/60 backdrop-blur px-6 py-3 shrink-0">
          <div className="flex items-center gap-2">
            {activeItem && <span className="text-lg">{activeItem.icon}</span>}
            <h2 className="text-white font-semibold">{activeItem?.label ?? activeTab}</h2>
          </div>
          <div className="ml-auto flex items-center gap-3">
            <span className="text-slate-500 text-sm hidden sm:block">{profile.full_name}</span>
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold shrink-0">
              {profile.full_name.charAt(0).toUpperCase()}
            </div>
          </div>
        </header>

        {/* Tab content */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8">
          <div className="max-w-3xl">
            {renderTab()}
          </div>
        </main>
      </div>
    </div>
  );
}
