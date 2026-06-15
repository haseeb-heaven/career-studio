import { useState } from "react";
import type { Profile, Education } from "../../types";
import { addEducation, updateEducation, deleteEducation } from "../../api";
import { useToast } from "../Toast";

interface Props {
  profile: Profile;
  onUpdate: (updated: Partial<Profile>) => void;
}

const EMPTY: Omit<Education, "id"> = { institution: "", degree: "", field: "", start: "", end: "" };

export default function EducationTab({ profile, onUpdate }: Props) {
  const { toast } = useToast();
  const [education, setEducation] = useState<Education[]>(profile.education ?? []);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState<Omit<Education, "id">>(EMPTY);
  const [adding, setAdding] = useState(false);
  const [addDraft, setAddDraft] = useState<Omit<Education, "id">>(EMPTY);
  const [saving, setSaving] = useState(false);

  const profileId = profile.id;
  const inputCls = "rounded border border-slate-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none w-full";

  async function handleAdd() {
    if (!addDraft.institution.trim()) return;
    setSaving(true);
    try {
      const created = await addEducation(profileId, addDraft);
      const next = [...education, created];
      setEducation(next);
      onUpdate({ education: next });
      setAddDraft(EMPTY);
      setAdding(false);
      toast("success", "Education added", created.institution);
    } catch {
      toast("error", "Failed to add education", "");
    } finally {
      setSaving(false);
    }
  }

  async function handleSave(eduId: number) {
    setSaving(true);
    try {
      const updated = await updateEducation(profileId, eduId, editDraft);
      const next = education.map((ed) => (ed.id === eduId ? updated : ed));
      setEducation(next);
      onUpdate({ education: next });
      setEditingId(null);
      toast("success", "Education updated", updated.institution);
    } catch {
      toast("error", "Failed to update education", "");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(eduId: number, name: string) {
    try {
      await deleteEducation(profileId, eduId);
      const next = education.filter((ed) => ed.id !== eduId);
      setEducation(next);
      onUpdate({ education: next });
      toast("success", "Education removed", name);
    } catch {
      toast("error", "Failed to delete education", "");
    }
  }

  function EduForm({ draft, setDraft, onSave, onCancel, label }: {
    draft: Omit<Education, "id">;
    setDraft: (d: Omit<Education, "id">) => void;
    onSave: () => void;
    onCancel: () => void;
    label: string;
  }) {
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="sm:col-span-2"><label className="block text-xs text-slate-500 mb-1">Institution *</label><input className={inputCls} value={draft.institution} onChange={(e) => setDraft({ ...draft, institution: e.target.value })} placeholder="MIT / Stanford / ..." autoFocus /></div>
          <div><label className="block text-xs text-slate-500 mb-1">Degree</label><input className={inputCls} value={draft.degree} onChange={(e) => setDraft({ ...draft, degree: e.target.value })} placeholder="BSc / MSc / PhD" /></div>
          <div><label className="block text-xs text-slate-500 mb-1">Field</label><input className={inputCls} value={draft.field} onChange={(e) => setDraft({ ...draft, field: e.target.value })} placeholder="Computer Science" /></div>
          <div><label className="block text-xs text-slate-500 mb-1">Start</label><input className={inputCls} value={draft.start} onChange={(e) => setDraft({ ...draft, start: e.target.value })} placeholder="2018" /></div>
          <div><label className="block text-xs text-slate-500 mb-1">End</label><input className={inputCls} value={draft.end} onChange={(e) => setDraft({ ...draft, end: e.target.value })} placeholder="2022" /></div>
        </div>
        <div className="flex gap-2">
          <button onClick={onSave} disabled={saving || !draft.institution.trim()} className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50">{label}</button>
          <button onClick={onCancel} className="rounded bg-slate-200 px-3 py-1 text-sm text-slate-600 hover:bg-slate-300">Cancel</button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800">Education</h2>
        <button
          onClick={() => { setAdding(true); setAddDraft(EMPTY); }}
          className="rounded-lg bg-blue-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-800"
        >
          + Add Education
        </button>
      </div>

      {education.length === 0 && !adding && (
        <p className="text-sm italic text-slate-400">No education on record.</p>
      )}

      {adding && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4">
          <p className="text-sm font-semibold text-green-800 mb-3">New Education</p>
          <EduForm draft={addDraft} setDraft={setAddDraft} onSave={handleAdd} onCancel={() => setAdding(false)} label="Add" />
        </div>
      )}

      <table className="w-full text-sm">
        <thead>
          {education.length > 0 && (
            <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
              <th className="pb-2 pr-4">Institution</th>
              <th className="pb-2 pr-4">Degree</th>
              <th className="pb-2 pr-4">Field</th>
              <th className="pb-2 pr-4">Period</th>
              <th className="pb-2 w-20" />
            </tr>
          )}
        </thead>
        <tbody>
          {education.map((ed) =>
            editingId === ed.id ? (
              <tr key={ed.id}>
                <td colSpan={5} className="py-3">
                  <div className="rounded-lg border border-blue-200 bg-blue-50 p-4">
                    <EduForm
                      draft={editDraft}
                      setDraft={setEditDraft}
                      onSave={() => handleSave(ed.id!)}
                      onCancel={() => setEditingId(null)}
                      label="Save"
                    />
                  </div>
                </td>
              </tr>
            ) : (
              <tr key={ed.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="py-2 pr-4 font-medium text-slate-800">{ed.institution}</td>
                <td className="py-2 pr-4 text-slate-600">{ed.degree}</td>
                <td className="py-2 pr-4 text-slate-600">{ed.field}</td>
                <td className="py-2 pr-4 text-slate-500">{ed.start}{ed.end ? ` – ${ed.end}` : ""}</td>
                <td className="py-2">
                  <div className="flex gap-1">
                    <button onClick={() => { setEditingId(ed.id!); setEditDraft({ institution: ed.institution, degree: ed.degree, field: ed.field, start: ed.start, end: ed.end }); }} className="text-xs text-blue-600 hover:underline">Edit</button>
                    <button onClick={() => handleDelete(ed.id!, ed.institution)} className="text-xs text-red-500 hover:underline">Del</button>
                  </div>
                </td>
              </tr>
            )
          )}
        </tbody>
      </table>
    </div>
  );
}
