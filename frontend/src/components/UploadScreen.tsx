import { useState, useRef } from "react";
import type { DragEvent } from "react";
import { importFile } from "../api";

interface Props {
  onImported: (profileId: number, warnings: string[]) => void;
}

const ACCEPTED = [".json", ".csv", ".xml", ".docx", ".doc", ".pdf"];

export default function UploadScreen({ onImported }: Props) {
  const [dragging, setDragging] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setError(null);
    setLoading(true);
    try {
      const result = await importFile(file);
      onImported(result.profile_id, result.warnings);
    } catch (e: unknown) {
      const msg =
        e instanceof Error
          ? e.message
          : "Upload failed — check backend is running on port 8000.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  }

  function onDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-100 p-8">
      <div className="w-full max-w-lg">
        <h1 className="mb-2 text-center text-3xl font-bold text-blue-900">
          Career Studio
        </h1>
        <p className="mb-8 text-center text-slate-500">
          Upload your resume to get started
        </p>

        <div
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          className={`
            cursor-pointer rounded-2xl border-2 border-dashed p-12 text-center
            transition-all duration-200
            ${dragging
              ? "border-blue-500 bg-blue-50 scale-[1.02]"
              : "border-slate-300 bg-white hover:border-blue-400 hover:bg-blue-50"}
          `}
        >
          <div className="mb-4 text-5xl">📄</div>
          <p className="mb-1 font-semibold text-slate-700">
            Drag &amp; drop a file here
          </p>
          <p className="text-sm text-slate-500">or click to browse</p>
          <p className="mt-3 text-xs text-slate-400">
            Supported: {ACCEPTED.join(", ")}
          </p>
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPTED.join(",")}
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0];
              if (file) handleFile(file);
            }}
          />
        </div>

        {loading && (
          <p className="mt-4 animate-pulse text-center text-blue-600">
            Parsing your file…
          </p>
        )}

        {error && (
          <div className="mt-4 rounded-lg border border-red-300 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        )}
      </div>
    </div>
  );
}
