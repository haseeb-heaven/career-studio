import type { Profile, Skill } from "../../types";

interface Props {
  profile: Profile;
}

export default function SkillsTab({ profile }: Props) {
  const skills: Skill[] = profile.skills ?? [];

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-800">Skills</h2>
      {skills.length === 0 ? (
        <p className="text-sm italic text-slate-400">No skills on record.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-200 text-left text-xs uppercase tracking-wide text-slate-500">
              <th className="pb-2 pr-4">Name</th>
              <th className="pb-2 pr-4">Category</th>
              <th className="pb-2">Years</th>
            </tr>
          </thead>
          <tbody>
            {skills.map((s) => (
              <tr key={s.id} className="border-b border-slate-100 hover:bg-slate-50">
                <td className="py-2 pr-4 font-medium text-slate-800">{s.name}</td>
                <td className="py-2 pr-4 text-slate-600">{s.category}</td>
                <td className="py-2 text-slate-600">{s.years}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
