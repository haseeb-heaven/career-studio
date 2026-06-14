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

const TABS = [
  "Contact",
  "Summary",
  "Skills",
  "Experience",
  "Projects",
  "Education",
  "Certifications",
  "Export",
] as const;

type TabName = (typeof TABS)[number];

interface Props {
  profileId: number;
  onBack: () => void;
}

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
        <div className="mb-6 flex flex-wrap gap-1 rounded-xl bg-white p-1 shadow-sm">
          {TABS.map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`
                rounded-lg px-4 py-2 text-sm font-medium transition-colors
                ${activeTab === tab
                  ? "bg-blue-700 text-white"
                  : "text-slate-600 hover:bg-slate-100"}
              `}
            >
              {tab}
            </button>
          ))}
        </div>

        <div className="rounded-xl bg-white p-6 shadow-sm">
          {renderTab()}
        </div>
      </div>
    </div>
  );
}
