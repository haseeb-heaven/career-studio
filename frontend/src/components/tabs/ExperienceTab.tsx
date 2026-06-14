import type { Profile } from "../../types";

interface Props {
  profile: Profile;
}

export default function ExperienceTab({ profile }: Props) {
  const experience = profile.experience ?? [];

  return (
    <div className="space-y-6">
      <h2 className="text-lg font-semibold text-slate-800">Experience</h2>
      {experience.length === 0 ? (
        <p className="text-sm italic text-slate-400">No experience on record.</p>
      ) : (
        experience.map((e) => (
          <div key={e.id} className="rounded-lg border border-slate-200 p-4">
            <div className="flex items-start justify-between">
              <div>
                <p className="font-semibold text-slate-800">{e.role}</p>
                <p className="text-sm text-blue-700">{e.company}</p>
              </div>
              <p className="text-xs text-slate-500">
                {e.start} – {e.end}
                {e.location ? ` · ${e.location}` : ""}
              </p>
            </div>
            {(e.bullets ?? []).length > 0 && (
              <ul className="mt-3 space-y-1">
                {e.bullets.map((b) => (
                  <li key={b.id} className="flex items-start gap-2 text-sm text-slate-700">
                    <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-blue-500" />
                    {b.text}
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))
      )}
    </div>
  );
}
