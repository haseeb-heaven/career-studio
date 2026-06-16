import { useState } from "react";
import type { Profile } from "../../types";
import { patchProfile } from "../../api";
import { useToast } from "../Toast";

interface Props {
  profile: Profile;
  onChange: (updated: Profile) => void;
}

export default function SummaryTab({ profile, onChange }: Props) {
  const { toast } = useToast();
  const [text, setText] = useState(profile.summary ?? "");
  const [availability, setAvailability] = useState(profile.availability ?? "");
  const [compensation, setCompensation] = useState(profile.compensation ?? "");
  const [saving, setSaving] = useState(false);

  async function save() {
    setSaving(true);
    try {
      await patchProfile(profile.id, { summary: text, availability, compensation });
      onChange({ ...profile, summary: text, availability, compensation });
      toast("success", "Summary saved", "");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-800">Summary &amp; Meta</h2>
      <div>
        <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
          Professional Summary
        </label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={5}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
            Availability
          </label>
          <input
            value={availability}
            onChange={(e) => setAvailability(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
            Compensation
          </label>
          <input
            value={compensation}
            onChange={(e) => setCompensation(e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>
      </div>
      <button
        onClick={save}
        disabled={saving}
        className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50"
      >
        {saving ? "Saving…" : "Save Summary"}
      </button>
    </div>
  );
}
