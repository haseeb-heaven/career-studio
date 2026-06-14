import type { Profile } from "../../types";

interface Props {
  profile: Profile;
}

export default function ProjectsTab({ profile }: Props) {
  const projects = profile.projects ?? [];

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-800">Projects</h2>
      {projects.length === 0 ? (
        <p className="text-sm italic text-slate-400">No projects on record.</p>
      ) : (
        projects.map((p) => (
          <div key={p.id} className="rounded-lg border border-slate-200 p-4">
            <div className="flex items-center justify-between">
              <p className="font-semibold text-slate-800">{p.name}</p>
              {p.link && (
                <a
                  href={p.link}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs text-blue-600 hover:underline"
                >
                  Link ↗
                </a>
              )}
            </div>
            {p.description && (
              <p className="mt-1 text-sm text-slate-600">{p.description}</p>
            )}
            {p.tech?.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {p.tech.map((t) => (
                  <span
                    key={t}
                    className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-800"
                  >
                    {t}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))
      )}
    </div>
  );
}
