import { useState } from "react";
import type { Profile } from "../../types";
import { patchProfile } from "../../api";
import { useToast } from "../Toast";

interface Props {
  profile: Profile;
  onChange: (updated: Profile) => void;
}

export default function ContactTab({ profile, onChange }: Props) {
  const { toast } = useToast();
  const [saving, setSaving] = useState(false);
  const [local, setLocal] = useState({
    full_name: profile.full_name,
    email: profile.email,
    phone: profile.phone,
    location: profile.location,
  });

  function field(label: string, key: keyof typeof local) {
    return (
      <div>
        <label className="mb-1 block text-xs font-medium uppercase tracking-wide text-slate-500">
          {label}
        </label>
        <input
          value={local[key]}
          onChange={(e) => setLocal({ ...local, [key]: e.target.value })}
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
      </div>
    );
  }

  async function save() {
    setSaving(true);
    try {
      await patchProfile(profile.id, local);
      onChange({ ...profile, ...local });
      toast("success", "Contact saved", "");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-800">Contact Info</h2>
      {field("Full Name", "full_name")}
      {field("Email", "email")}
      {field("Phone", "phone")}
      {field("Location", "location")}

      {profile.links?.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-medium uppercase tracking-wide text-slate-500">
            Links
          </p>
          <ul className="space-y-1 text-sm">
            {profile.links.map((lnk) => (
              <li key={lnk.id} className="flex items-center gap-2">
                <span className="font-medium text-slate-700">{lnk.label}:</span>
                <a
                  href={lnk.url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-blue-600 hover:underline"
                >
                  {lnk.url}
                </a>
              </li>
            ))}
          </ul>
        </div>
      )}

      <button
        onClick={save}
        disabled={saving}
        className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-medium text-white hover:bg-blue-800 disabled:opacity-50"
      >
        {saving ? "Saving…" : "Save Contact"}
      </button>
    </div>
  );
}
