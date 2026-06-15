import { useState } from "react";
import type { Profile, Project } from "../../types";
import { addProject, updateProject, deleteProject } from "../../api";
import { useToast } from "../Toast";

interface Props {
  profile: Profile;
  onUpdate: (updated: Partial<Profile>) => void;
}

const EMPTY: Omit<Project, "id"> = { name: "", description: "", link: "", tech: [] };

export default function ProjectsTab({ profile, onUpdate }: Props) {
  const { toast } = useToast();
  const [projects, setProjects] = useState<Project[]>(profile.projects ?? []);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState<Omit<Project, "id">>(EMPTY);
  const [adding, setAdding] = useState(false);
  const [addDraft, setAddDraft] = useState<Omit<Project, "id">>(EMPTY);
  const [saving, setSaving] = useState(false);

  const profileId = profile.id;
  const inputCls = "rounded border border-slate-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none w-full";

  function parseTech(val: string): string[] {
    return val.split(",").map((t) => t.trim()).filter(Boolean);
  }

  async function handleAdd() {
    if (!addDraft.name.trim()) return;
    setSaving(true);
    try {
      const created = await addProject(profileId, addDraft);
      const next = [...projects, created];
      setProjects(next);
      onUpdate({ projects: next });
      setAddDraft(EMPTY);
      setAdding(false);
      toast("success", "Project added", created.name);
    } catch {
      toast("error", "Failed to add project", "");
    } finally {
      setSaving(false);
    }
  }

  async function handleSave(projId: number) {
    setSaving(true);
    try {
      const updated = await updateProject(profileId, projId, editDraft);
      const next = projects.map((p) => (p.id === projId ? updated : p));
      setProjects(next);
      onUpdate({ projects: next });
      setEditingId(null);
      toast("success", "Project updated", updated.name);
    } catch {
      toast("error", "Failed to update project", "");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(projId: number, name: string) {
    try {
      await deleteProject(profileId, projId);
      const next = projects.filter((p) => p.id !== projId);
      setProjects(next);
      onUpdate({ projects: next });
      toast("success", "Project removed", name);
    } catch {
      toast("error", "Failed to delete project", "");
    }
  }

  function ProjectForm({ draft, setDraft, onSave, onCancel, label }: {
    draft: Omit<Project, "id">;
    setDraft: (d: Omit<Project, "id">) => void;
    onSave: () => void;
    onCancel: () => void;
    label: string;
  }) {
    return (
      <div className="space-y-3">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="sm:col-span-2"><label className="block text-xs text-slate-500 mb-1">Name *</label><input className={inputCls} value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} placeholder="Project name" autoFocus /></div>
          <div className="sm:col-span-2"><label className="block text-xs text-slate-500 mb-1">Description</label><textarea className={`${inputCls} resize-none`} rows={2} value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} placeholder="What does it do?" /></div>
          <div><label className="block text-xs text-slate-500 mb-1">Link</label><input className={inputCls} value={draft.link} onChange={(e) => setDraft({ ...draft, link: e.target.value })} placeholder="https://github.com/..." /></div>
          <div><label className="block text-xs text-slate-500 mb-1">Tech (comma-separated)</label><input className={inputCls} value={draft.tech.join(", ")} onChange={(e) => setDraft({ ...draft, tech: parseTech(e.target.value) })} placeholder="React, Python, Docker" /></div>
        </div>
        <div className="flex gap-2">
          <button onClick={onSave} disabled={saving || !draft.name.trim()} className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50">{label}</button>
          <button onClick={onCancel} className="rounded bg-slate-200 px-3 py-1 text-sm text-slate-600 hover:bg-slate-300">Cancel</button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800">Projects</h2>
        <button
          onClick={() => { setAdding(true); setAddDraft(EMPTY); }}
          className="rounded-lg bg-blue-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-800"
        >
          + Add Project
        </button>
      </div>

      {projects.length === 0 && !adding && (
        <p className="text-sm italic text-slate-400">No projects on record.</p>
      )}

      {adding && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4">
          <p className="text-sm font-semibold text-green-800 mb-3">New Project</p>
          <ProjectForm draft={addDraft} setDraft={setAddDraft} onSave={handleAdd} onCancel={() => setAdding(false)} label="Add" />
        </div>
      )}

      {projects.map((p) => (
        <div key={p.id} className="rounded-lg border border-slate-200 p-4">
          {editingId === p.id ? (
            <ProjectForm
              draft={editDraft}
              setDraft={setEditDraft}
              onSave={() => handleSave(p.id!)}
              onCancel={() => setEditingId(null)}
              label="Save"
            />
          ) : (
            <>
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="font-semibold text-slate-800">{p.name}</p>
                    {p.link && (
                      <a href={p.link} target="_blank" rel="noreferrer" className="text-xs text-blue-600 hover:underline shrink-0">Link ↗</a>
                    )}
                  </div>
                  {p.description && <p className="mt-1 text-sm text-slate-600">{p.description}</p>}
                  {p.tech?.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {p.tech.map((t) => (
                        <span key={t} className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-800">{t}</span>
                      ))}
                    </div>
                  )}
                </div>
                <div className="flex gap-2 shrink-0 ml-3">
                  <button onClick={() => { setEditingId(p.id!); setEditDraft({ name: p.name, description: p.description, link: p.link, tech: p.tech ?? [] }); }} className="text-xs text-blue-600 hover:underline">Edit</button>
                  <button onClick={() => handleDelete(p.id!, p.name)} className="text-xs text-red-500 hover:underline">Delete</button>
                </div>
              </div>
            </>
          )}
        </div>
      ))}
    </div>
  );
}
