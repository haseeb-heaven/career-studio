import { useState } from "react";
import type { Profile, Experience, ExperienceBullet } from "../../types";
import {
  addExperience, updateExperience, deleteExperience,
  addBullet, updateBullet, deleteBullet,
} from "../../api";
import { useToast } from "../Toast";

interface Props {
  profile: Profile;
  onUpdate: (updated: Partial<Profile>) => void;
}

const EMPTY_EXP: Omit<Experience, "id"> = { company: "", role: "", start: "", end: "", location: "", bullets: [] };

export default function ExperienceTab({ profile, onUpdate }: Props) {
  const { toast } = useToast();
  const [experience, setExperience] = useState<Experience[]>(profile.experience ?? []);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState<Omit<Experience, "id" | "bullets">>({ company: "", role: "", start: "", end: "", location: "" });
  const [adding, setAdding] = useState(false);
  const [addDraft, setAddDraft] = useState<Omit<Experience, "id">>(EMPTY_EXP);
  const [saving, setSaving] = useState(false);
  const [editingBullet, setEditingBullet] = useState<{ expId: number; bulletId: number } | null>(null);
  const [bulletDraft, setBulletDraft] = useState("");
  const [addingBulletExpId, setAddingBulletExpId] = useState<number | null>(null);
  const [newBulletText, setNewBulletText] = useState("");

  const profileId = profile.id;
  const inputCls = "rounded border border-slate-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none w-full";

  async function handleAdd() {
    if (!addDraft.company.trim() && !addDraft.role.trim()) return;
    setSaving(true);
    try {
      const created = await addExperience(profileId, addDraft);
      const next = [created, ...experience];
      setExperience(next);
      onUpdate({ experience: next });
      setAddDraft(EMPTY_EXP);
      setAdding(false);
      toast("success", "Experience added", `${created.role} at ${created.company}`);
    } catch {
      toast("error", "Failed to add experience", "");
    } finally {
      setSaving(false);
    }
  }

  async function handleSave(expId: number) {
    setSaving(true);
    try {
      const updated = await updateExperience(profileId, expId, editDraft);
      const next = experience.map((e) => e.id === expId ? { ...e, ...updated } : e);
      setExperience(next);
      onUpdate({ experience: next });
      setEditingId(null);
      toast("success", "Experience updated", updated.role);
    } catch {
      toast("error", "Failed to update experience", "");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(expId: number) {
    try {
      await deleteExperience(profileId, expId);
      const next = experience.filter((e) => e.id !== expId);
      setExperience(next);
      onUpdate({ experience: next });
      toast("success", "Experience removed", "");
    } catch {
      toast("error", "Failed to delete experience", "");
    }
  }

  async function handleAddBullet(expId: number) {
    if (!newBulletText.trim()) return;
    try {
      const bullet = await addBullet(profileId, expId, newBulletText);
      const next = experience.map((e) =>
        e.id === expId ? { ...e, bullets: [...(e.bullets || []), bullet] } : e
      );
      setExperience(next);
      onUpdate({ experience: next });
      setNewBulletText("");
      setAddingBulletExpId(null);
    } catch {
      toast("error", "Failed to add bullet", "");
    }
  }

  async function handleSaveBullet(expId: number, bulletId: number) {
    try {
      const updated = await updateBullet(profileId, expId, bulletId, bulletDraft);
      const next = experience.map((e) =>
        e.id === expId
          ? { ...e, bullets: (e.bullets || []).map((b) => (b.id === bulletId ? updated : b)) }
          : e
      );
      setExperience(next);
      onUpdate({ experience: next });
      setEditingBullet(null);
    } catch {
      toast("error", "Failed to update bullet", "");
    }
  }

  async function handleDeleteBullet(expId: number, bulletId: number) {
    try {
      await deleteBullet(profileId, expId, bulletId);
      const next = experience.map((e) =>
        e.id === expId
          ? { ...e, bullets: (e.bullets || []).filter((b) => b.id !== bulletId) }
          : e
      );
      setExperience(next);
      onUpdate({ experience: next });
    } catch {
      toast("error", "Failed to delete bullet", "");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800">Experience</h2>
        <button
          onClick={() => { setAdding(true); setAddDraft(EMPTY_EXP); }}
          className="rounded-lg bg-blue-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-800"
        >
          + Add Experience
        </button>
      </div>

      {experience.length === 0 && !adding && (
        <p className="text-sm italic text-slate-400">No experience on record.</p>
      )}

      {adding && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4 space-y-3">
          <p className="text-sm font-semibold text-green-800">New Experience</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div><label className="block text-xs text-slate-500 mb-1">Role *</label><input className={inputCls} value={addDraft.role} onChange={(e) => setAddDraft({ ...addDraft, role: e.target.value })} placeholder="Software Engineer" autoFocus /></div>
            <div><label className="block text-xs text-slate-500 mb-1">Company *</label><input className={inputCls} value={addDraft.company} onChange={(e) => setAddDraft({ ...addDraft, company: e.target.value })} placeholder="Acme Corp" /></div>
            <div><label className="block text-xs text-slate-500 mb-1">Start</label><input className={inputCls} value={addDraft.start} onChange={(e) => setAddDraft({ ...addDraft, start: e.target.value })} placeholder="Jan 2022" /></div>
            <div><label className="block text-xs text-slate-500 mb-1">End</label><input className={inputCls} value={addDraft.end} onChange={(e) => setAddDraft({ ...addDraft, end: e.target.value })} placeholder="Present" /></div>
            <div className="sm:col-span-2"><label className="block text-xs text-slate-500 mb-1">Location</label><input className={inputCls} value={addDraft.location} onChange={(e) => setAddDraft({ ...addDraft, location: e.target.value })} placeholder="Remote / City, Country" /></div>
          </div>
          <div className="flex gap-2">
            <button onClick={handleAdd} disabled={saving} className="rounded bg-green-600 px-3 py-1 text-sm text-white hover:bg-green-700 disabled:opacity-50">Add</button>
            <button onClick={() => setAdding(false)} className="rounded bg-slate-200 px-3 py-1 text-sm text-slate-600 hover:bg-slate-300">Cancel</button>
          </div>
        </div>
      )}

      {experience.map((e) => (
        <div key={e.id} className="rounded-lg border border-slate-200 p-4 space-y-3">
          {editingId === e.id ? (
            <div className="space-y-3">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div><label className="block text-xs text-slate-500 mb-1">Role</label><input className={inputCls} value={editDraft.role} onChange={(ev) => setEditDraft({ ...editDraft, role: ev.target.value })} autoFocus /></div>
                <div><label className="block text-xs text-slate-500 mb-1">Company</label><input className={inputCls} value={editDraft.company} onChange={(ev) => setEditDraft({ ...editDraft, company: ev.target.value })} /></div>
                <div><label className="block text-xs text-slate-500 mb-1">Start</label><input className={inputCls} value={editDraft.start} onChange={(ev) => setEditDraft({ ...editDraft, start: ev.target.value })} /></div>
                <div><label className="block text-xs text-slate-500 mb-1">End</label><input className={inputCls} value={editDraft.end} onChange={(ev) => setEditDraft({ ...editDraft, end: ev.target.value })} /></div>
                <div className="sm:col-span-2"><label className="block text-xs text-slate-500 mb-1">Location</label><input className={inputCls} value={editDraft.location} onChange={(ev) => setEditDraft({ ...editDraft, location: ev.target.value })} /></div>
              </div>
              <div className="flex gap-2">
                <button onClick={() => handleSave(e.id!)} disabled={saving} className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50">Save</button>
                <button onClick={() => setEditingId(null)} className="rounded bg-slate-200 px-3 py-1 text-sm text-slate-600 hover:bg-slate-300">Cancel</button>
              </div>
            </div>
          ) : (
            <div className="flex items-start justify-between">
              <div>
                <p className="font-semibold text-slate-800">{e.role}</p>
                <p className="text-sm text-blue-700">{e.company}</p>
                <p className="text-xs text-slate-500">{e.start}{e.end ? ` – ${e.end}` : ""}{e.location ? ` · ${e.location}` : ""}</p>
              </div>
              <div className="flex gap-2 shrink-0">
                <button onClick={() => { setEditingId(e.id!); setEditDraft({ company: e.company, role: e.role, start: e.start, end: e.end, location: e.location }); }} className="text-xs text-blue-600 hover:underline">Edit</button>
                <button onClick={() => handleDelete(e.id!)} className="text-xs text-red-500 hover:underline">Delete</button>
              </div>
            </div>
          )}

          {/* Bullets */}
          <ul className="space-y-1 pl-1">
            {(e.bullets ?? []).map((b) => (
              <li key={b.id} className="flex items-start gap-2 group">
                {editingBullet?.expId === e.id && editingBullet?.bulletId === b.id ? (
                  <div className="flex-1 flex gap-1">
                    <input className={inputCls} value={bulletDraft} onChange={(ev) => setBulletDraft(ev.target.value)} autoFocus onKeyDown={(ev) => ev.key === "Enter" && handleSaveBullet(e.id!, b.id!)} />
                    <button onClick={() => handleSaveBullet(e.id!, b.id!)} className="shrink-0 rounded bg-blue-600 px-2 text-xs text-white">Save</button>
                    <button onClick={() => setEditingBullet(null)} className="shrink-0 rounded bg-slate-200 px-2 text-xs text-slate-600">✕</button>
                  </div>
                ) : (
                  <>
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-blue-500" />
                    <span className="flex-1 text-sm text-slate-700">{b.text}</span>
                    <div className="hidden group-hover:flex gap-1 shrink-0">
                      <button onClick={() => { setEditingBullet({ expId: e.id!, bulletId: b.id! }); setBulletDraft(b.text); }} className="text-xs text-blue-500 hover:underline">edit</button>
                      <button onClick={() => handleDeleteBullet(e.id!, b.id!)} className="text-xs text-red-400 hover:underline">del</button>
                    </div>
                  </>
                )}
              </li>
            ))}
          </ul>

          {/* Add bullet */}
          {addingBulletExpId === e.id ? (
            <div className="flex gap-1 pl-4">
              <input className={`${inputCls} flex-1`} placeholder="New bullet point…" value={newBulletText} onChange={(ev) => setNewBulletText(ev.target.value)} autoFocus onKeyDown={(ev) => ev.key === "Enter" && handleAddBullet(e.id!)} />
              <button onClick={() => handleAddBullet(e.id!)} className="shrink-0 rounded bg-blue-600 px-2 text-xs text-white">Add</button>
              <button onClick={() => { setAddingBulletExpId(null); setNewBulletText(""); }} className="shrink-0 rounded bg-slate-200 px-2 text-xs text-slate-600">✕</button>
            </div>
          ) : (
            <button onClick={() => { setAddingBulletExpId(e.id!); setNewBulletText(""); }} className="text-xs text-slate-400 hover:text-blue-600 pl-4">+ Add bullet</button>
          )}
        </div>
      ))}
    </div>
  );
}
