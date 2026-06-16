import { exportProfileBlob } from "../api";

interface Props {
  profileId: number;
  fullName: string;
}

const FORMATS = [
  { fmt: "json",      label: "JSON",      icon: "{ }" },
  { fmt: "csv",       label: "CSV",       icon: "⊞" },
  { fmt: "xml",       label: "XML",       icon: "</>" },
  { fmt: "docx",      label: "DOCX",      icon: "W" },
  { fmt: "pdf",       label: "PDF",       icon: "⬇" },
  { fmt: "latex",     label: "LaTeX",     icon: "λ" },
  { fmt: "portfolio", label: "Portfolio", icon: "🌐" },
] as const;

export default function ExportPanel({ profileId, fullName }: Props) {
  async function download(fmt: string) {
    try {
      const blob = await exportProfileBlob(profileId, fmt);
      let extension = fmt;
      if (fmt === "portfolio") {
        extension = "html";
      } else if (fmt === "latex") {
        extension = "tex";
      }
      const cleanName = fullName.replace(/[^\w\-]/g, "_").replace(/^_+|_+$/g, "") || "profile";
      const filename = `${cleanName}.${extension}`;

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed:", err);
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-lg font-semibold text-slate-800">Export Profile</h2>
      <p className="text-sm text-slate-500">
        Download your profile in any of the supported formats.
      </p>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-5">
        {FORMATS.map(({ fmt, label, icon }) => (
          <button
            key={fmt}
            onClick={() => download(fmt)}
            className="flex flex-col items-center gap-2 rounded-xl border border-slate-200 bg-white p-4 transition-all hover:border-blue-400 hover:bg-blue-50"
          >
            <span className="font-mono text-2xl text-blue-700">{icon}</span>
            <span className="text-sm font-medium text-slate-700">{label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
