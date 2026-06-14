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

const TABS = [
  "Contact",
  "Summary",
  "Skills",
  "Experience",
  "Projects",
  "Education",
  "Certifications",
  "Export",
  "Analysis",
  "Cover Letter",
  "Roadmap",
  "Jobs",
  "Logs",
  "Settings",
] as const;

type TabName = (typeof TABS)[number];

interface Props {
  profileId: number;
  onBack: () => void;
}

const TAB_GROUPS = [
  { label: "Profile",   tabs: ["Contact", "Summary", "Skills", "Experience", "Projects", "Education", "Certifications"] },
  { label: "AI",        tabs: ["Analysis", "Cover Letter", "Roadmap", "Jobs"] },
  { label: "Export",    tabs: ["Export"] },
  { label: "System",    tabs: ["Logs", "Settings"] },
] as const;

export default function ProfileEditor({ profileId, onBack }: Props) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [activeTab, setActiveTab] = useState<TabName>("Contact");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getProfile(profileId)
      .then(setProfile)
      .finally(() => setLoading(false));
  }, [profileId]);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="animate-pulse text-blue-600">Loading profile…</p>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="p-8 text-red-600">Failed to load profile #{profileId}</div>
    );
  }

  function renderTab() {
    if (!profile) return null;
    switch (activeTab) {
      case "Contact":        return <ContactTab profile={profile} onChange={setProfile} />;
      case "Summary":        return <SummaryTab profile={profile} onChange={setProfile} />;
      case "Skills":         return <SkillsTab profile={profile} />;
      case "Experience":     return <ExperienceTab profile={profile} />;
      case "Projects":       return <ProjectsTab profile={profile} />;
      case "Education":      return <EducationTab profile={profile} />;
      case "Certifications": return <CertificationsTab profile={profile} />;
      case "Export":         return <ExportPanel profileId={profile.id} fullName={profile.full_name} />;
      case "Analysis":       return <AnalysisTab profileId={profile.id} />;
      case "Cover Letter":   return <CoverLetterTab profileId={profile.id} />;
      case "Roadmap":        return <RoadmapTab profileId={profile.id} />;
      case "Jobs":           return <JobsTab profileId={profile.id} />;
      case "Logs":           return <LogsTab />;
      case "Settings":       return <SettingsTab />;
    }
  }

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="flex items-center gap-4 bg-blue-900 px-6 py-4 text-white shadow">
        <button
          onClick={onBack}
          className="rounded px-2 py-1 text-sm hover:bg-blue-800"
        >
          ← Upload
        </button>
        <h1 className="text-xl font-bold">{profile.full_name}</h1>
        <span className="ml-auto text-sm text-blue-300">Profile #{profile.id}</span>
      </header>

      <div className="mx-auto max-w-5xl p-6">
        {/* Tab group navigation */}
        <div className="mb-2 space-y-1">
          {TAB_GROUPS.map((group) => (
            <div key={group.label} className="flex items-center gap-1 flex-wrap">
              <span className="w-16 shrink-0 text-xs font-semibold text-slate-400 uppercase tracking-wide">
                {group.label}
              </span>
              {group.tabs.map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab as TabName)}
                  className={`
                    rounded-lg px-3 py-1.5 text-xs font-medium transition-colors
                    ${activeTab === tab
                      ? "bg-blue-700 text-white"
                      : "bg-white text-slate-600 hover:bg-slate-100 border border-slate-200"}
                  `}
                >
                  {tab}
                </button>
              ))}
            </div>
          ))}
        </div>

        <div className="mt-4 rounded-xl bg-white p-6 shadow-sm">
          {renderTab()}
        </div>
      </div>
    </div>
  );
}
