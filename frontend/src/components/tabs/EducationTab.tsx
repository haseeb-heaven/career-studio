import type { Profile } from "../../types";

interface Props {
  profile: Profile;
}

export default function EducationTab({ profile }: Props) {
  const education = profile.education ?? [];

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-800">Education</h2>
      {education.length === 0 ? (
        <p className="text-sm italic text-slate-400">No education on record.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
              <th className="pb-2 pr-4">Institution</th>
              <th className="pb-2 pr-4">Degree</th>
              <th className="pb-2 pr-4">Field</th>
              <th className="pb-2">Period</th>
            </tr>
          </thead>
          <tbody>
            {education.map((ed) => (
              <tr key={ed.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="py-2 pr-4 font-medium text-slate-800">{ed.institution}</td>
                <td className="py-2 pr-4 text-slate-600">{ed.degree}</td>
                <td className="py-2 pr-4 text-slate-600">{ed.field}</td>
                <td className="py-2 text-slate-500">
                  {ed.start} – {ed.end}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
