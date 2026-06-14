import type { Profile } from "../../types";

interface Props {
  profile: Profile;
}

export default function CertificationsTab({ profile }: Props) {
  const certs = profile.certifications ?? [];

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-800">Certifications</h2>
      {certs.length === 0 ? (
        <p className="text-sm italic text-slate-400">No certifications on record.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
              <th className="pb-2 pr-4">Name</th>
              <th className="pb-2 pr-4">Issuer</th>
              <th className="pb-2">Date</th>
            </tr>
          </thead>
          <tbody>
            {certs.map((c) => (
              <tr key={c.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="py-2 pr-4 font-medium text-slate-800">{c.name}</td>
                <td className="py-2 pr-4 text-slate-600">{c.issuer}</td>
                <td className="py-2 text-slate-500">{c.date}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
