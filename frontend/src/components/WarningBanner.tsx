interface Props {
  warnings: string[];
}

export default function WarningBanner({ warnings }: Props) {
  if (!warnings.length) return null;
  return (
    <div className="mb-4 rounded-lg border border-yellow-300 bg-yellow-50 p-4">
      <p className="mb-1 font-semibold text-yellow-800">
        Import warnings ({warnings.length})
      </p>
      <ul className="list-inside list-disc space-y-1 text-sm text-yellow-700">
        {warnings.map((w, i) => (
          <li key={i}>{w}</li>
        ))}
      </ul>
    </div>
  );
}
