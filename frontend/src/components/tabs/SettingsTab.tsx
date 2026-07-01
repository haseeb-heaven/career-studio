import { useState, useEffect } from "react";
import { getSettings, updateSettings, testApiKey } from "../../api";
import axios from "axios";

const BASE = "http://localhost:8000/api";

const EXTERNAL_PROVIDERS = ["openai", "anthropic", "openrouter", "gemini", "cerebras", "groq", "nvidia"] as const;

const PROVIDER_LABELS: Record<string, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  openrouter: "OpenRouter",
  gemini: "Gemini",
  cerebras: "Cerebras",
  groq: "Groq",
  nvidia: "NVIDIA",
};

const PROVIDER_KEY_PLACEHOLDER: Record<string, string> = {
  openai: "sk-…  (leave blank to keep existing key)",
  anthropic: "sk-ant-…  (leave blank to keep existing key)",
  openrouter: "sk-or-…  (leave blank to keep existing key)",
  gemini: "AIza…  (leave blank to keep existing key)",
  cerebras: "csk-…  (leave blank to keep existing key)",
  groq: "gsk_…  (leave blank to keep existing key)",
  nvidia: "nvapi-…  (leave blank to keep existing key)",
};

const FREE_OPENROUTER_MODELS = [
  { model: "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", use_case: "reasoning" },
  { model: "nvidia/nemotron-3-super-120b-a12b:free", use_case: "general reasoning" },
  { model: "nvidia/nemotron-3-nano-30b-a3b:free", use_case: "general" },
  { model: "nvidia/nemotron-nano-12b-v2-vl:free", use_case: "vision-language" },
  { model: "nvidia/nemotron-nano-9b-v2:free", use_case: "general" },
  { model: "nvidia/nemotron-3-ultra-550b-a55b:free", use_case: "heavy reasoning" },
  { model: "google/gemma-4-31b-it:free", use_case: "general" },
  { model: "google/gemma-4-26b-a4b-it:free", use_case: "general" },
  { model: "google/gemma-3-27b-it:free", use_case: "general" },
  { model: "google/gemma-3-12b-it:free", use_case: "lightweight" },
  { model: "google/gemma-3-4b-it:free", use_case: "edge" },
  { model: "google/gemma-3n-e4b-it:free", use_case: "edge vision" },
  { model: "google/gemma-3n-e2b-it:free", use_case: "edge vision" },
  { model: "meta-llama/llama-3.3-70b-instruct:free", use_case: "instruct" },
  { model: "meta-llama/llama-3.2-3b-instruct:free", use_case: "lightweight" },
  { model: "openai/gpt-oss-120b:free", use_case: "general reasoning" },
  { model: "openai/gpt-oss-20b:free", use_case: "light general" },
  { model: "qwen/qwen3-coder:free", use_case: "coding / structured output" },
  { model: "qwen/qwen3-next-80b-a3b-instruct:free", use_case: "instruct" },
  { model: "liquid/lfm-2.5-1.2b-thinking:free", use_case: "thinking" },
  { model: "liquid/lfm-2.5-1.2b-instruct:free", use_case: "lightweight fallback" },
  { model: "z-ai/glm-4.5-air:free", use_case: "general" },
  { model: "arcee-ai/trinity-large-preview:free", use_case: "general" },
  { model: "cognitivecomputations/dolphin-mistral-24b-venice-edition:free", use_case: "general" },
  { model: "nousresearch/hermes-3-llama-3.1-405b:free", use_case: "heavy reasoning" },
  { model: "meta-llama/llama-3.1-8b-instruct:free", use_case: "lightweight fallback" },
  { model: "mistralai/mistral-7b-instruct:free", use_case: "general" },
  { model: "mistralai/mistral-small-3.2-24b-instruct:free", use_case: "general" },
  { model: "deepseek/deepseek-chat-v3.1:free", use_case: "general reasoning" },
  { model: "deepseek/deepseek-r1:free", use_case: "heavy reasoning" },
  { model: "qwen/qwen-2.5-72b-instruct:free", use_case: "instruct" },
  { model: "microsoft/mai-ds-r1:free", use_case: "general reasoning" }
];

const PREMIUM_OPENROUTER_MODELS = [
  { model: "z-ai/glm-5.2", use_case: "long-horizon coding / agentic", price: "$1.15/$3.62 per M" },
  { model: "moonshotai/kimi-k2.6", use_case: "coding / multi-agent orchestration", price: "$0.55/$3.20 per M" },
  { model: "deepseek/deepseek-v4", use_case: "frontier reasoning / coding", price: "varies" },
  { model: "anthropic/claude-opus-4.8", use_case: "top-tier reasoning", price: "premium" },
  { model: "openai/gpt-5.2", use_case: "top-tier general", price: "premium" },
];

const EXTERNAL_MODELS: Record<string, string[]> = {
  openai:      ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
  anthropic:   ["claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-opus-4-8"],
  openrouter:  FREE_OPENROUTER_MODELS.map((m) => m.model),
  gemini:      ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"],
  cerebras:    ["llama-3.3-70b", "llama-4-scout", "gpt-oss-120b"],
  groq:        ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "gemma2-9b-it"],
  nvidia:      ["nvidia/nemotron-3-super-120b-a12b", "nvidia/nemotron-3-nano-30b-a3b", "meta/llama-3.3-70b-instruct"],
};

const OLLAMA_POPULAR = ["llama3.2", "llama3.1", "mistral", "mistral-nemo", "gemma2", "codellama", "phi3", "deepseek-r1"];

type AIMode = "local" | "external";

interface OllamaStatus {
  available: boolean;
  models: string[];
}

export default function SettingsTab() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [activeSection, setActiveSection] = useState<"ai" | "routing" | "jobs" | "about">("ai");

  // Form state
  const [mode, setMode] = useState<AIMode>("external");
  const [externalProvider, setExternalProvider] = useState("openai");
  const [externalModel, setExternalModel] = useState("gpt-4o-mini");
  const [customModel, setCustomModel] = useState("");
  const [openaiKey, setOpenaiKey] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [openrouterKey, setOpenrouterKey] = useState("");
  const [geminiKey, setGeminiKey] = useState("");
  const [cerebrasKey, setCerebrasKey] = useState("");
  const [groqKey, setGroqKey] = useState("");
  const [nvidiaKey, setNvidiaKey] = useState("");
  const [ollamaUrl, setOllamaUrl] = useState("http://localhost:11434");
  const [ollamaModel, setOllamaModel] = useState("llama3.2");
  const [customOllamaModel, setCustomOllamaModel] = useState("");
  const [localForSimple, setLocalForSimple] = useState(true);
  const [deepSemanticMatching, setDeepSemanticMatching] = useState(false);
  const [adzunaId, setAdzunaId] = useState("");
  const [adzunaKey, setAdzunaKey] = useState("");
  const [linkedinKey, setLinkedinKey] = useState("");
  const [indeedKey, setIndeedKey] = useState("");
  const [glassdoorKey, setGlassdoorKey] = useState("");
  const [ollamaStatus, setOllamaStatus] = useState<OllamaStatus | null>(null);
  const [checkingOllama, setCheckingOllama] = useState(false);
  const [keyTestStatus, setKeyTestStatus] = useState<Record<string, { ok: boolean; message: string } | null>>({});
  const [testingKey, setTestingKey] = useState<string | null>(null);

  const KEY_STATE: Record<string, [string, (v: string) => void]> = {
    openai: [openaiKey, setOpenaiKey],
    anthropic: [anthropicKey, setAnthropicKey],
    openrouter: [openrouterKey, setOpenrouterKey],
    gemini: [geminiKey, setGeminiKey],
    cerebras: [cerebrasKey, setCerebrasKey],
    groq: [groqKey, setGroqKey],
    nvidia: [nvidiaKey, setNvidiaKey],
  };

  useEffect(() => {
    getSettings().then((s) => {
      // Settings API returns strings or booleans; coerce booleans defensively
      const boolVal = (v: any) => v === true || v === "true" || v === "1" || v === 1;
      setMode(boolVal(s.use_local_ai) ? "local" : "external");
      
      const providerVal = s.ai_provider ?? "openai";
      const modelVal = s.ai_model ?? "gpt-4o-mini";
      setExternalProvider(providerVal);
      setExternalModel(modelVal);

      // Pre-populate customModel if it's a custom model ID not in our lists
      if (providerVal === "openrouter") {
        const isPredefined = FREE_OPENROUTER_MODELS.some((m) => m.model === modelVal);
        if (!isPredefined) {
          setCustomModel(modelVal);
        }
      } else {
        const isPredefined = EXTERNAL_MODELS[providerVal]?.includes(modelVal);
        if (!isPredefined) {
          setCustomModel(modelVal);
        }
      }

      setOllamaUrl(s.ollama_base_url ?? "http://localhost:11434");
      setOllamaModel(s.ollama_model ?? "llama3.2");
      setLocalForSimple(boolVal(s.local_for_simple) || s.local_for_simple === "");
      setDeepSemanticMatching(boolVal(s.use_deep_semantic_matching));
      
      // Pre-populate keys
      if (s.api_key) setOpenaiKey(s.api_key);
      if (s.anthropic_api_key) setAnthropicKey(s.anthropic_api_key);
      if (s.openrouter_api_key) setOpenrouterKey(s.openrouter_api_key);
      if (s.gemini_api_key) setGeminiKey(s.gemini_api_key);
      if (s.cerebras_api_key) setCerebrasKey(s.cerebras_api_key);
      if (s.groq_api_key) setGroqKey(s.groq_api_key);
      if (s.nvidia_api_key) setNvidiaKey(s.nvidia_api_key);
      if (s.adzuna_app_id) setAdzunaId(s.adzuna_app_id);
      if (s.adzuna_app_key) setAdzunaKey(s.adzuna_app_key);
      if (s.linkedin_api_key) setLinkedinKey(s.linkedin_api_key);
      if (s.indeed_api_key) setIndeedKey(s.indeed_api_key);
      if (s.glassdoor_api_key) setGlassdoorKey(s.glassdoor_api_key);
    }).finally(() => setLoading(false));
  }, []);

  async function checkOllama() {
    setCheckingOllama(true);
    try {
      const res = await axios.get(`${BASE}/settings/ollama/status?base_url=${encodeURIComponent(ollamaUrl)}`);
      setOllamaStatus(res.data);
    } catch {
      setOllamaStatus({ available: false, models: [] });
    } finally {
      setCheckingOllama(false);
    }
  }

  async function handleTestKey(provider: string, keyValue: string) {
    setTestingKey(provider);
    try {
      const result = await testApiKey(provider, keyValue);
      setKeyTestStatus((prev) => ({ ...prev, [provider]: result }));
    } catch {
      setKeyTestStatus((prev) => ({ ...prev, [provider]: { ok: false, message: "Could not reach the backend." } }));
    } finally {
      setTestingKey(null);
    }
  }

  async function save() {
    setSaving(true);
    try {
      const payload: Record<string, string | boolean> = {
        ai_provider: externalProvider,
        ai_model: customModel || externalModel,
        use_local_ai: mode === "local",
        ollama_base_url: ollamaUrl,
        ollama_model: customOllamaModel || ollamaModel,
        local_for_simple: localForSimple,
        use_deep_semantic_matching: deepSemanticMatching,
        adzuna_app_id: adzunaId,
      };
      if (openaiKey) payload.api_key = openaiKey;
      if (anthropicKey) payload.anthropic_api_key = anthropicKey;
      if (openrouterKey) payload.openrouter_api_key = openrouterKey;
      if (geminiKey) payload.gemini_api_key = geminiKey;
      if (cerebrasKey) payload.cerebras_api_key = cerebrasKey;
      if (groqKey) payload.groq_api_key = groqKey;
      if (nvidiaKey) payload.nvidia_api_key = nvidiaKey;
      if (adzunaKey) payload.adzuna_app_key = adzunaKey;
      if (linkedinKey) payload.linkedin_api_key = linkedinKey;
      if (indeedKey) payload.indeed_api_key = indeedKey;
      if (glassdoorKey) payload.glassdoor_api_key = glassdoorKey;
      await updateSettings(payload as Record<string, string>);
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
    } finally {
      setSaving(false);
    }
  }

  if (loading) return <p className="animate-pulse text-blue-400">Loading settings…</p>;

  const sections = [
    { id: "ai" as const, icon: "🤖", label: "AI Provider" },
    { id: "routing" as const, icon: "🔀", label: "Task Routing" },
    { id: "jobs" as const, icon: "💼", label: "Job Search" },
    { id: "about" as const, icon: "ℹ️", label: "About" },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-white">Settings</h2>
        <p className="text-sm text-slate-400 mt-0.5">Configure AI providers, task routing, and preferences.</p>
      </div>

      {/* Section tabs */}
      <div className="flex gap-1 bg-slate-800/60 rounded-xl p-1 border border-slate-700/40">
        {sections.map((sec) => (
          <button
            key={sec.id}
            onClick={() => setActiveSection(sec.id)}
            className={`flex-1 flex items-center justify-center gap-2 rounded-lg py-2 text-sm font-medium transition-all ${
              activeSection === sec.id
                ? "bg-blue-600 text-white shadow-sm"
                : "text-slate-400 hover:text-slate-200"
            }`}
          >
            <span>{sec.icon}</span>
            <span>{sec.label}</span>
          </button>
        ))}
      </div>

      {/* ── AI Provider section ── */}
      {activeSection === "ai" && (
        <div className="space-y-6">
          {/* Mode toggle */}
          <div className="rounded-2xl border border-slate-700/40 bg-slate-800/40 p-5 space-y-4">
            <h3 className="text-white font-semibold text-sm">AI Mode</h3>
            <div className="grid grid-cols-2 gap-3">
              <button
                onClick={() => setMode("local")}
                className={`rounded-xl border-2 p-4 text-left transition-all ${
                  mode === "local"
                    ? "border-green-500 bg-green-500/10"
                    : "border-slate-700 bg-slate-800/40 hover:border-slate-500"
                }`}
              >
                <div className="text-2xl mb-2">🏠</div>
                <p className={`font-semibold text-sm ${mode === "local" ? "text-green-400" : "text-slate-300"}`}>
                  Local AI (Ollama)
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Runs entirely on your machine. No API keys, no cost, full privacy. Requires Ollama installed.
                </p>
              </button>
              <button
                onClick={() => setMode("external")}
                className={`rounded-xl border-2 p-4 text-left transition-all ${
                  mode === "external"
                    ? "border-blue-500 bg-blue-500/10"
                    : "border-slate-700 bg-slate-800/40 hover:border-slate-500"
                }`}
              >
                <div className="text-2xl mb-2">☁️</div>
                <p className={`font-semibold text-sm ${mode === "external" ? "text-blue-400" : "text-slate-300"}`}>
                  External API
                </p>
                <p className="text-xs text-slate-500 mt-1">
                  Use OpenAI, Anthropic, or OpenRouter. Better results for complex tasks.
                </p>
              </button>
            </div>
          </div>

          {/* Local AI config */}
          {mode === "local" && (
            <div className="rounded-2xl border border-slate-700/40 bg-slate-800/40 p-5 space-y-4">
              <h3 className="text-white font-semibold text-sm">Ollama Configuration</h3>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Ollama Server URL</label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={ollamaUrl}
                    onChange={(e) => setOllamaUrl(e.target.value)}
                    className="flex-1 rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                  />
                  <button
                    onClick={checkOllama}
                    disabled={checkingOllama}
                    className="rounded-lg bg-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-600 disabled:opacity-50 shrink-0"
                  >
                    {checkingOllama ? "Checking…" : "Test"}
                  </button>
                </div>
                {ollamaStatus && (
                  <p className={`mt-1.5 text-xs font-medium ${ollamaStatus.available ? "text-green-400" : "text-red-400"}`}>
                    {ollamaStatus.available
                      ? `✅ Connected — ${ollamaStatus.models.length} model(s) available`
                      : "❌ Cannot reach Ollama — make sure it's running: ollama serve"}
                  </p>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-400 mb-1.5">Model</label>
                <div className="flex flex-wrap gap-2">
                  {(ollamaStatus?.models.length ? ollamaStatus.models : OLLAMA_POPULAR).map((m) => (
                    <button
                      key={m}
                      onClick={() => setOllamaModel(m)}
                      className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
                        ollamaModel === m
                          ? "bg-green-600 border-green-600 text-white"
                          : "border-slate-600 text-slate-400 hover:border-slate-400"
                      }`}
                    >
                      {m}
                    </button>
                  ))}
                </div>
                <input
                  type="text"
                  placeholder="Or type a custom model name (e.g. mistral-nemo:latest)"
                  value={customOllamaModel}
                  onChange={(e) => setCustomOllamaModel(e.target.value)}
                  className="mt-2 w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-blue-500 focus:outline-none"
                />
              </div>

              <div className="rounded-xl bg-slate-900/60 border border-green-500/20 p-3">
                <p className="text-xs text-green-400 font-semibold mb-1">Don't have Ollama yet?</p>
                <p className="text-xs text-slate-400">
                  Install from <span className="text-slate-300">ollama.ai</span>, then run:{" "}
                  <code className="bg-slate-800 px-1.5 py-0.5 rounded text-green-300">ollama pull llama3.2</code>
                </p>
              </div>
            </div>
          )}

          {/* External API config */}
          {mode === "external" && (
            <div className="rounded-2xl border border-slate-700/40 bg-slate-800/40 p-5 space-y-5">
              <h3 className="text-white font-semibold text-sm">External API Configuration</h3>

              {/* Provider selector */}
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-2">Provider</label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {EXTERNAL_PROVIDERS.map((p) => (
                    <button
                      key={p}
                      onClick={() => {
                        setExternalProvider(p);
                        setExternalModel(EXTERNAL_MODELS[p][0]);
                        setCustomModel("");
                      }}
                      className={`rounded-xl py-2.5 text-sm font-semibold border-2 transition-all ${
                        externalProvider === p
                          ? "border-blue-500 bg-blue-500/15 text-blue-300"
                          : "border-slate-700 text-slate-400 hover:border-slate-500"
                      }`}
                    >
                      {PROVIDER_LABELS[p]}
                    </button>
                  ))}
                </div>
              </div>

              {/* Model */}
              <div>
                <label className="block text-xs font-medium text-slate-400 mb-2">Model</label>
                {externalProvider === "openrouter" ? (
                  <select
                    value={customModel || externalModel}
                    onChange={(e) => {
                      const val = e.target.value;
                      const isFreeModel = FREE_OPENROUTER_MODELS.some((m) => m.model === val);
                      if (isFreeModel) {
                        setExternalModel(val);
                        setCustomModel("");
                      } else {
                        setCustomModel(val);
                      }
                    }}
                    className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-slate-200 focus:border-blue-500 focus:outline-none"
                  >
                    <option value="" disabled>-- Select an OpenRouter Model --</option>
                    <optgroup label="Free">
                      {FREE_OPENROUTER_MODELS.map((m) => (
                        <option key={m.model} value={m.model}>
                          {m.model} ({m.use_case})
                        </option>
                      ))}
                    </optgroup>
                    <optgroup label="Premium (paid)">
                      {PREMIUM_OPENROUTER_MODELS.map((m) => (
                        <option key={m.model} value={m.model}>
                          {m.model} ({m.use_case} — {m.price})
                        </option>
                      ))}
                    </optgroup>
                    {customModel &&
                      !FREE_OPENROUTER_MODELS.some(m => m.model === customModel) &&
                      !PREMIUM_OPENROUTER_MODELS.some(m => m.model === customModel) && (
                      <option value={customModel}>
                        {customModel} (Custom)
                      </option>
                    )}
                  </select>
                ) : (
                  <div className="flex flex-wrap gap-2">
                    {EXTERNAL_MODELS[externalProvider].map((m) => (
                      <button
                        key={m}
                        onClick={() => { setExternalModel(m); setCustomModel(""); }}
                        className={`rounded-full px-3 py-1 text-xs font-medium border transition-colors ${
                          externalModel === m && !customModel
                            ? "bg-blue-600 border-blue-600 text-white"
                            : "border-slate-600 text-slate-400 hover:border-slate-400"
                        }`}
                      >
                        {m}
                      </button>
                    ))}
                  </div>
                )}
                <input
                  type="text"
                  placeholder="Or enter a custom model ID (e.g. meta-llama/llama-3.1-405b)…"
                  value={customModel}
                  onChange={(e) => {
                    const val = e.target.value;
                    setCustomModel(val);
                    if (!val && externalProvider === "openrouter") {
                      setExternalModel(FREE_OPENROUTER_MODELS[0].model);
                    }
                  }}
                  className="mt-2 w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-blue-500 focus:outline-none"
                />
              </div>

              {/* API Key */}
              {(() => {
                const [keyValue, setKeyValue] = KEY_STATE[externalProvider];
                const status = keyTestStatus[externalProvider];
                return (
                  <div>
                    <label className="block text-xs font-medium text-slate-400 mb-1.5">
                      {PROVIDER_LABELS[externalProvider]} API Key
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="password"
                        placeholder={PROVIDER_KEY_PLACEHOLDER[externalProvider]}
                        value={keyValue}
                        onChange={(e) => setKeyValue(e.target.value)}
                        className="flex-1 rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-blue-500 focus:outline-none"
                      />
                      <button
                        onClick={() => handleTestKey(externalProvider, keyValue)}
                        disabled={testingKey === externalProvider || !keyValue}
                        className="rounded-lg bg-slate-700 px-4 py-2 text-xs font-semibold text-slate-200 hover:bg-slate-600 disabled:opacity-50 shrink-0"
                      >
                        {testingKey === externalProvider ? "Testing…" : "Test"}
                      </button>
                    </div>
                    {status && (
                      <p className={`mt-1.5 text-xs font-medium ${status.ok ? "text-green-400" : "text-red-400"}`}>
                        {status.ok ? `✅ ${status.message}` : `❌ ${status.message}`}
                      </p>
                    )}
                  </div>
                );
              })()}
            </div>
          )}
        </div>
      )}

      {/* ── Task Routing section ── */}
      {activeSection === "routing" && (
        <div className="rounded-2xl border border-slate-700/40 bg-slate-800/40 p-5 space-y-5">
          <h3 className="text-white font-semibold text-sm">Task Routing Strategy</h3>
          <p className="text-slate-400 text-xs">
            Control which AI engine handles each type of task. Routing only applies when both local and external are configured.
          </p>

          <div className="space-y-3">
            <label className="flex items-start gap-4 rounded-xl border border-slate-700 bg-slate-900/50 p-4 cursor-pointer hover:border-slate-500 transition-colors">
              <input
                type="radio"
                name="routing"
                checked={localForSimple && mode === "local"}
                onChange={() => { setLocalForSimple(true); setMode("local"); }}
                className="mt-1 accent-green-500"
              />
              <div>
                <p className="text-slate-200 text-sm font-semibold">🏠 Always Local (Ollama)</p>
                <p className="text-slate-400 text-xs mt-1">
                  All tasks run on your machine. No API costs. Requires Ollama with a capable model.
                </p>
              </div>
            </label>

            <label className="flex items-start gap-4 rounded-xl border border-slate-700 bg-slate-900/50 p-4 cursor-pointer hover:border-slate-500 transition-colors">
              <input
                type="radio"
                name="routing"
                checked={localForSimple && mode !== "local"}
                onChange={() => { setLocalForSimple(true); setMode("external"); }}
                className="mt-1 accent-blue-500"
              />
              <div>
                <p className="text-slate-200 text-sm font-semibold">🔀 Smart Routing (Recommended)</p>
                <p className="text-slate-400 text-xs mt-1">
                  Simple tasks (quick analysis, keyword extraction) → Local AI.<br />
                  Heavy tasks (cover letters, roadmaps, full analysis) → External API.<br />
                  Best quality + lowest cost.
                </p>
              </div>
            </label>

            <label className="flex items-start gap-4 rounded-xl border border-slate-700 bg-slate-900/50 p-4 cursor-pointer hover:border-slate-500 transition-colors">
              <input
                type="radio"
                name="routing"
                checked={!localForSimple && mode === "external"}
                onChange={() => { setLocalForSimple(false); setMode("external"); }}
                className="mt-1 accent-blue-500"
              />
              <div>
                <p className="text-slate-200 text-sm font-semibold">☁️ Always External API</p>
                <p className="text-slate-400 text-xs mt-1">
                  All tasks use your configured external API. Best results, API costs apply.
                </p>
              </div>
            </label>
          </div>
        </div>
      )}

      {activeSection === "jobs" && (
        <div className="rounded-2xl border border-slate-700/40 bg-slate-800/40 p-5 space-y-5">
          <h3 className="text-white font-semibold text-sm">Job Search Configuration</h3>
          <p className="text-slate-400 text-xs">
            Configure external job boards. By default, the app searches public APIs like Remotive, RemoteOK, and Arbeitnow. To enable Adzuna, provide your credentials.
          </p>

          <label className="flex items-start gap-4 rounded-xl border border-slate-700 bg-slate-900/50 p-4 cursor-pointer hover:border-slate-500 transition-colors">
            <input
              type="checkbox"
              checked={deepSemanticMatching}
              onChange={(e) => setDeepSemanticMatching(e.target.checked)}
              className="mt-1 accent-blue-500"
            />
            <div>
              <p className="text-slate-200 text-sm font-semibold">🧠 Deep Semantic Matching (local AI)</p>
              <p className="text-slate-400 text-xs mt-1">
                Uses a small local language model (downloaded once, ~80MB) to catch matches that don't share exact
                keywords — e.g. a resume bullet about "event-stream processing" matching a job asking for "data
                pipelines". Runs entirely on your machine after the first download; no data is sent to any external
                API. Slightly slower search.
              </p>
            </div>
          </label>

          <div className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Adzuna App ID (Optional API)</label>
              <input
                type="text"
                placeholder="e.g. 12345678"
                value={adzunaId}
                onChange={(e) => setAdzunaId(e.target.value)}
                className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Adzuna API Key (Optional API)</label>
              <input
                type="password"
                placeholder="e.g. abcd1234efgh5678... (leave blank to keep existing key)"
                value={adzunaKey}
                onChange={(e) => setAdzunaKey(e.target.value)}
                className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div className="border-t border-slate-800 my-4 pt-4">
              <h4 className="text-white text-xs font-semibold mb-3">API Keys / Tokens (Last Resort)</h4>
              <p className="text-[11px] text-slate-400 mb-4 leading-relaxed">
                By default, job searches on LinkedIn, Indeed, and Glassdoor run without APIs (preferred). Provide API keys only if guest scraping gets rate-limited.
              </p>
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">LinkedIn API Key / Scraping Token</label>
              <input
                type="password"
                placeholder="leave blank to use guest search (preferred)"
                value={linkedinKey}
                onChange={(e) => setLinkedinKey(e.target.value)}
                className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Indeed API Key / Token</label>
              <input
                type="password"
                placeholder="leave blank to use guest search (preferred)"
                value={indeedKey}
                onChange={(e) => setIndeedKey(e.target.value)}
                className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="block text-xs font-medium text-slate-400 mb-1.5">Glassdoor API Key / Token</label>
              <input
                type="password"
                placeholder="leave blank to use guest search (preferred)"
                value={glassdoorKey}
                onChange={(e) => setGlassdoorKey(e.target.value)}
                className="w-full rounded-lg bg-slate-900 border border-slate-700 px-3 py-2 text-sm text-slate-200 placeholder-slate-600 focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>
        </div>
      )}

      {activeSection === "about" && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-slate-700/40 bg-slate-800/40 p-5 space-y-3">
            <div className="flex items-center gap-3">
              <span className="text-3xl">🎓</span>
              <div>
                <p className="text-white font-bold">Career Studio</p>
                <p className="text-slate-400 text-xs">Version 2.0 — Slice 2 Complete</p>
              </div>
            </div>
            <p className="text-slate-400 text-sm">
              A local-first, AI-ready career management platform. Parse any resume format → edit → export to 7 formats → AI analysis, cover letters, roadmaps, and live job matching.
            </p>
          </div>
          <div className="rounded-2xl border border-slate-700/40 bg-slate-800/40 p-5 space-y-2">
            <p className="text-white font-semibold text-sm">Built with love by</p>
            <p className="text-slate-400 text-sm">
              <span className="text-blue-400 font-semibold">Haseeb Mir</span> · entirely built using{" "}
              <span className="text-blue-400 font-semibold">Claude Code</span> (Anthropic's agentic coding CLI).
            </p>
            <p className="text-slate-500 text-xs">
              Special gratitude to the teams behind Claude Fable and Claude Mythos — the models pushing the frontier of AI-assisted engineering.
            </p>
          </div>
          <div className="rounded-2xl border border-slate-700/40 bg-slate-800/40 p-5">
            <p className="text-white font-semibold text-sm mb-3">API Endpoints</p>
            <p className="text-slate-400 text-xs">Backend: <span className="font-mono text-blue-400">http://localhost:8000</span></p>
            <p className="text-slate-400 text-xs">Docs: <span className="font-mono text-blue-400">http://localhost:8000/docs</span></p>
          </div>
        </div>
      )}

      {/* Save button */}
      {activeSection !== "about" && (
        <button
          onClick={save}
          disabled={saving}
          className="w-full rounded-xl bg-blue-600 py-3 text-sm font-bold text-white hover:bg-blue-500 disabled:opacity-50 transition-colors"
        >
          {saving ? "Saving…" : saved ? "✅ Saved!" : "Save Settings"}
        </button>
      )}
    </div>
  );
}
