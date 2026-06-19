import { useState } from "react";
import type { Profile, Certification } from "../../types";
import { addCertification, updateCertification, deleteCertification } from "../../api";
import { useToast } from "../Toast";

interface Props {
  profile: Profile;
  onUpdate: (updated: Partial<Profile>) => void;
}

const EMPTY: Omit<Certification, "id"> = { name: "", cert_id: "", issuer: "", date: "" };

export default function CertificationsTab({ profile, onUpdate }: Props) {
  const { toast } = useToast();
  const [certs, setCerts] = useState<Certification[]>(profile.certifications ?? []);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState<Omit<Certification, "id">>(EMPTY);
  const [adding, setAdding] = useState(false);
  const [addDraft, setAddDraft] = useState<Omit<Certification, "id">>(EMPTY);
  const [saving, setSaving] = useState(false);

  const profileId = profile.id;
  const inputCls = "rounded border border-slate-300 px-2 py-1 text-sm focus:border-blue-500 focus:outline-none w-full";

  async function handleAdd() {
    if (!addDraft.name.trim()) return;
    setSaving(true);
    try {
      const created = await addCertification(profileId, addDraft);
      const next = [...certs, created];
      setCerts(next);
      onUpdate({ certifications: next });
      setAddDraft(EMPTY);
      setAdding(false);
      toast("success", "Certification added", created.name);
    } catch {
      toast("error", "Failed to add certification", "");
    } finally {
      setSaving(false);
    }
  }

  async function handleSave(certId: number) {
    setSaving(true);
    try {
      const updated = await updateCertification(profileId, certId, editDraft);
      const next = certs.map((c) => (c.id === certId ? updated : c));
      setCerts(next);
      onUpdate({ certifications: next });
      setEditingId(null);
      toast("success", "Certification updated", updated.name);
    } catch {
      toast("error", "Failed to update certification", "");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(certId: number, name: string) {
    try {
      await deleteCertification(profileId, certId);
      const next = certs.filter((c) => c.id !== certId);
      setCerts(next);
      onUpdate({ certifications: next });
      toast("success", "Certification removed", name);
    } catch {
      toast("error", "Failed to delete certification", "");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-800">Certifications</h2>
        <button
          onClick={() => { setAdding(true); setAddDraft(EMPTY); }}
          className="rounded-lg bg-blue-700 px-3 py-1.5 text-xs font-semibold text-white hover:bg-blue-800"
        >
          + Add Certification
        </button>
      </div>

      {certs.length === 0 && !adding && (
        <p className="text-sm italic text-slate-400">No certifications on record.</p>
      )}

      {adding && (
        <div className="rounded-lg border border-green-200 bg-green-50 p-4 space-y-3">
          <p className="text-sm font-semibold text-green-800">New Certification</p>
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <div><label className="block text-xs text-slate-500 mb-1">Name *</label><input className={inputCls} value={addDraft.name} onChange={(e) => setAddDraft({ ...addDraft, name: e.target.value })} placeholder="AWS Solutions Architect" autoFocus /></div>
            <div><label className="block text-xs text-slate-500 mb-1">Cert ID</label><input className={inputCls} value={addDraft.cert_id || ""} onChange={(e) => setAddDraft({ ...addDraft, cert_id: e.target.value })} placeholder="e.g. AWS-SAA-12345" /></div>
            <div><label className="block text-xs text-slate-500 mb-1">Issuer</label><input className={inputCls} value={addDraft.issuer} onChange={(e) => setAddDraft({ ...addDraft, issuer: e.target.value })} placeholder="Amazon" /></div>
            <div><label className="block text-xs text-slate-500 mb-1">Date</label><input type="date" className={inputCls} value={addDraft.date} onChange={(e) => setAddDraft({ ...addDraft, date: e.target.value })} /></div>
          </div>
          <div className="flex gap-2">
            <button onClick={handleAdd} disabled={saving || !addDraft.name.trim()} className="rounded bg-green-600 px-3 py-1 text-sm text-white hover:bg-green-700 disabled:opacity-50">Add</button>
            <button onClick={() => setAdding(false)} className="rounded bg-slate-200 px-3 py-1 text-sm text-slate-600 hover:bg-slate-300">Cancel</button>
          </div>
        </div>
      )}

      <table className="w-full text-sm">
        <thead>
          {certs.length > 0 && (
            <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
              <th className="pb-2 pr-4">Name</th>
              <th className="pb-2 pr-4">Cert ID</th>
              <th className="pb-2 pr-4">Issuer</th>
              <th className="pb-2 pr-4">Date</th>
              <th className="pb-2 w-24" />
            </tr>
          )}
        </thead>
        <tbody>
          {certs.map((c) =>
            editingId === c.id ? (
              <tr key={c.id}>
                <td colSpan={5} className="py-3">
                  <div className="rounded-lg border border-blue-200 bg-blue-50 p-3 space-y-3">
                    <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                      <div><label className="block text-xs text-slate-500 mb-1">Name</label><input className={inputCls} value={editDraft.name} onChange={(e) => setEditDraft({ ...editDraft, name: e.target.value })} autoFocus /></div>
                      <div><label className="block text-xs text-slate-500 mb-1">Cert ID</label><input className={inputCls} value={editDraft.cert_id || ""} onChange={(e) => setEditDraft({ ...editDraft, cert_id: e.target.value })} placeholder="alphanumeric" /></div>
                      <div><label className="block text-xs text-slate-500 mb-1">Issuer</label><input className={inputCls} value={editDraft.issuer} onChange={(e) => setEditDraft({ ...editDraft, issuer: e.target.value })} /></div>
                      <div><label className="block text-xs text-slate-500 mb-1">Date</label><input type="date" className={inputCls} value={editDraft.date} onChange={(e) => setEditDraft({ ...editDraft, date: e.target.value })} /></div>
                    </div>
                    <div className="flex gap-2">
                      <button onClick={() => handleSave(c.id!)} disabled={saving} className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50">Save</button>
                      <button onClick={() => setEditingId(null)} className="rounded bg-slate-200 px-3 py-1 text-sm text-slate-600 hover:bg-slate-300">Cancel</button>
                    </div>
                  </div>
                </td>
              </tr>
            ) : (
              <tr key={c.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="py-2 pr-4 font-medium text-slate-800">{c.name}</td>
                <td className="py-2 pr-4 font-mono text-xs text-slate-700">{c.cert_id || "—"}</td>
                <td className="py-2 pr-4 text-slate-600">{c.issuer}</td>
                <td className="py-2 pr-4 text-slate-500">{c.date}</td>
                <td className="py-2">
                  <div className="flex gap-1">
                    <button onClick={() => { setEditingId(c.id!); setEditDraft({ name: c.name, cert_id: c.cert_id || "", issuer: c.issuer, date: c.date }); }} className="text-xs text-blue-600 hover:underline">Edit</button>
                    <button onClick={() => handleDelete(c.id!, c.name)} className="text-xs text-red-500 hover:underline">Del</button>
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
