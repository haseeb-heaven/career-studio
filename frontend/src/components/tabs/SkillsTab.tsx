import { useState } from "react";
import type { Profile, Skill } from "../../types";
import { addSkill, updateSkill, deleteSkill } from "../../api";
import { useToast } from "../Toast";

interface Props {
  profile: Profile;
  onUpdate: (updated: Partial<Profile>) => void;
}

const EMPTY: Omit<Skill, "id"> = { name: "", category: "", years: 0 };

export default function SkillsTab({ profile, onUpdate }: Props) {
  const { toast } = useToast();
  const [skills, setSkills] = useState<Skill[]>(profile.skills ?? []);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState<Omit<Skill, "id">>(EMPTY);
  const [adding, setAdding] = useState(false);
  const [addDraft, setAddDraft] = useState<Omit<Skill, "id">>(EMPTY);
  const [saving, setSaving] = useState(false);

  const profileId = profile.id;

  async function handleAdd() {
    if (!addDraft.name.trim()) return;
    setSaving(true);
    try {
      const created = await addSkill(profileId, addDraft);
      const next = [...skills, created];
      setSkills(next);
      onUpdate({ skills: next });
      setAddDraft(EMPTY);
      setAdding(false);
      toast("success", "Skill added", addDraft.name);
    } catch {
      toast("error", "Failed to add skill", "");
    } finally {
      setSaving(false);
    }
  }

  async function handleSave(skillId: number) {
    setSaving(true);
    try {
      const updated = await updateSkill(profileId, skillId, editDraft);
      const next = skills.map((s) => (s.id === skillId ? updated : s));
      setSkills(next);
      onUpdate({ skills: next });
      setEditingId(null);
      toast("success", "Skill updated", updated.name);
    } catch {
      toast("error", "Failed to update skill", "");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(skillId: number, name: string) {
    try {
      await deleteSkill(profileId, skillId);
      const next = skills.filter((s) => s.id !== skillId);
      setSkills(next);
      onUpdate({ skills: next });
      toast("success", "Skill removed", name);
    } catch {
      toast("error", "Failed to delete skill", "");
    }
  }

  const inputCls = "rounded border border-slate-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none w-full";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800">Skills</h2>
        <button
          onClick={() => { setAdding(true); setAddDraft(EMPTY); }}
          className="rounded-lg bg-blue-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-800"
        >
          + Add Skill
        </button>
      </div>

      {skills.length === 0 && !adding && (
        <p className="text-sm italic text-slate-400">No skills on record.</p>
      )}

      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
            <th className="pb-2 pr-4">Name</th>
            <th className="pb-2 pr-4">Category</th>
            <th className="pb-2 pr-4">Years</th>
            <th className="pb-2 w-20" />
          </tr>
        </thead>
        <tbody>
          {skills.map((s) =>
            editingId === s.id ? (
              <tr key={s.id} className="border-b border-blue-100 bg-blue-50">
                <td className="py-1.5 pr-2"><input className={inputCls} value={editDraft.name} onChange={(e) => setEditDraft({ ...editDraft, name: e.target.value })} autoFocus /></td>
                <td className="py-1.5 pr-2"><input className={inputCls} value={editDraft.category} onChange={(e) => setEditDraft({ ...editDraft, category: e.target.value })} /></td>
                <td className="py-1.5 pr-2"><input className={inputCls} type="number" min={0} step={0.5} value={editDraft.years} onChange={(e) => setEditDraft({ ...editDraft, years: parseFloat(e.target.value) || 0 })} /></td>
                <td className="py-1.5">
                  <div className="flex gap-1">
                    <button onClick={() => handleSave(s.id!)} disabled={saving} className="rounded bg-blue-600 px-2 py-0.5 text-xs text-white hover:bg-blue-700 disabled:opacity-50">Save</button>
                    <button onClick={() => setEditingId(null)} className="rounded bg-slate-200 px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-300">Cancel</button>
                  </div>
                </td>
              </tr>
            ) : (
              <tr key={s.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="py-2 pr-4 font-medium text-slate-800">{s.name}</td>
                <td className="py-2 pr-4 text-slate-600">{s.category}</td>
                <td className="py-2 pr-4 text-slate-600">{s.years}</td>
                <td className="py-2">
                  <div className="flex gap-1">
                    <button onClick={() => { setEditingId(s.id!); setEditDraft({ name: s.name, category: s.category, years: s.years }); }} className="rounded px-2 py-0.5 text-xs text-blue-600 hover:bg-blue-50">Edit</button>
                    <button onClick={() => handleDelete(s.id!, s.name)} className="rounded px-2 py-0.5 text-xs text-red-500 hover:bg-red-50">Del</button>
                  </div>
                </td>
              </tr>
            )
          )}

          {adding && (
            <tr className="border-b border-green-100 bg-green-50">
              <td className="py-1.5 pr-2"><input className={inputCls} placeholder="Skill name" value={addDraft.name} onChange={(e) => setAddDraft({ ...addDraft, name: e.target.value })} autoFocus onKeyDown={(e) => e.key === "Enter" && handleAdd()} /></td>
              <td className="py-1.5 pr-2"><input className={inputCls} placeholder="Category" value={addDraft.category} onChange={(e) => setAddDraft({ ...addDraft, category: e.target.value })} /></td>
              <td className="py-1.5 pr-2"><input className={inputCls} type="number" min={0} step={0.5} placeholder="0" value={addDraft.years || ""} onChange={(e) => setAddDraft({ ...addDraft, years: parseFloat(e.target.value) || 0 })} /></td>
              <td className="py-1.5">
                <div className="flex gap-1">
                  <button onClick={handleAdd} disabled={saving || !addDraft.name.trim()} className="rounded bg-green-600 px-2 py-0.5 text-xs text-white hover:bg-green-700 disabled:opacity-50">Add</button>
                  <button onClick={() => setAdding(false)} className="rounded bg-slate-200 px-2 py-0.5 text-xs text-slate-600 hover:bg-slate-300">Cancel</button>
                </div>
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
