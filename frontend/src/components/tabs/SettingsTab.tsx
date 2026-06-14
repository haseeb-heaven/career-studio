import { useState, useEffect } from "react";
import { getSettings, updateSettings } from "../../api";

const PROVIDERS = ["openai", "anthropic", "openrouter"] as const;

const DEFAULT_MODELS: Record<string, string[]> = {
  openai: ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
  anthropic: ["claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-opus-4-8"],
  openrouter: ["openai/gpt-4o-mini", "anthropic/claude-haiku-4-5-20251001", "google/gemini-flash-1.5", "meta-llama/llama-3.1-8b-instruct:free"],
};

export default function SettingsTab() {
  const [form, setForm] = useState({
    ai_provider: "openai",
    ai_model: "gpt-4o-mini",
    api_key: "",
    anthropic_api_key: "",
    openrouter_api_key: "",
  });
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getSettings()
      .then((s) => setForm((f) => ({ ...f, ...s, api_key: "", anthropic_api_key: "", openrouter_api_key: "" })))
      .finally(() => setLoading(false));
  }, []);

  function handleChange(key: string, val: string) {
    setForm((f) => ({ ...f, [key]: val }));
  }

  async function save() {
    setSaving(true);
    try {
      const payload: Record<string, string> = { ai_provider: form.ai_provider, ai_model: form.ai_model };
      if (form.api_key) payload.api_key = form.api_key;
      if (form.anthropic_api_key) payload.anthropic_api_key = form.anthropic_api_key;
      if (form.openrouter_api_key) payload.openrouter_api_key = form.openrouter_api_key;
      await updateSettings(payload);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="animate-pulse text-blue-600">Loading settings…</p>;

  const models = DEFAULT_MODELS[form.ai_provider] ?? [];

  return (
    <div className="space-y-6 max-w-lg">
      <h2 className="text-lg font-semibold text-slate-800">AI Settings</h2>
      <p className="text-sm text-slate-500">
        Configure which AI provider to use for resume analysis, cover letters, and roadmap generation.
        API keys are stored locally in SQLite and never sent anywhere except the chosen provider.
      </p>

      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Provider</label>
          <div className="flex gap-2">
            {PROVIDERS.map((p) => (
              <button
                key={p}
                onClick={() => {
                  const defaultModel = DEFAULT_MODELS[p][0];
                  setForm((f) => ({ ...f, ai_provider: p, ai_model: defaultModel }));
                }}
                className={`px-4 py-2 rounded-lg text-sm font-medium border transition-colors ${
                  form.ai_provider === p
                    ? "bg-blue-700 text-white border-blue-700"
                    : "bg-white text-slate-600 border-slate-300 hover:border-blue-400"
                }`}
              >
                {p === "openai" ? "OpenAI" : p === "anthropic" ? "Anthropic" : "OpenRouter"}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Model</label>
          <select
            value={form.ai_model}
            onChange={(e) => handleChange("ai_model", e.target.value)}
            className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          >
            {models.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Or type a custom model name…"
            value={models.includes(form.ai_model) ? "" : form.ai_model}
            onChange={(e) => handleChange("ai_model", e.target.value)}
            className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
        </div>

        {form.ai_provider === "openai" && (
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">OpenAI API Key</label>
            <input
              type="password"
              placeholder="sk-…  (leave blank to keep existing)"
              value={form.api_key}
              onChange={(e) => handleChange("api_key", e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
        )}

        {form.ai_provider === "anthropic" && (
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">Anthropic API Key</label>
            <input
              type="password"
              placeholder="sk-ant-…  (leave blank to keep existing)"
              value={form.anthropic_api_key}
              onChange={(e) => handleChange("anthropic_api_key", e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
        )}

        {form.ai_provider === "openrouter" && (
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">OpenRouter API Key</label>
            <input
              type="password"
              placeholder="sk-or-…  (leave blank to keep existing)"
              value={form.openrouter_api_key}
              onChange={(e) => handleChange("openrouter_api_key", e.target.value)}
              className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
        )}
      </div>

      <button
        onClick={save}
        disabled={saving}
        className="rounded-lg bg-blue-700 px-6 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-50"
      >
        {saving ? "Saving…" : saved ? "Saved ✓" : "Save Settings"}
      </button>
    </div>
  );
}
