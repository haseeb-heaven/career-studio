import { useState } from "react";
import type { AuthUser } from "../types";
import { register, login, setAuthToken } from "../api";

interface Props {
  onAuth: (user: AuthUser) => void;
  onGuest: () => void;
}

type Tab = "login" | "register";

export default function LoginScreen({ onAuth, onGuest }: Props) {
  const [tab, setTab] = useState<Tab>("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      let result;
      if (tab === "register") {
        result = await register(username.trim(), password, email.trim());
      } else {
        result = await login(username.trim(), password);
      }
      setAuthToken(result.access_token);
      localStorage.setItem("auth_token", result.access_token);
      localStorage.setItem("auth_user", JSON.stringify({ user_id: result.user_id, username: result.username }));
      onAuth({ user_id: result.user_id, username: result.username, token: result.access_token });
    } catch (err: unknown) {
      const axiosErr = err as { response?: { data?: { detail?: string } } };
      setError(axiosErr?.response?.data?.detail ?? "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "var(--color-bg)",
      padding: "1rem",
    }}>
      <div style={{
        background: "var(--color-surface)",
        border: "1px solid var(--color-border)",
        borderRadius: "12px",
        padding: "2rem",
        width: "100%",
        maxWidth: "400px",
        boxShadow: "0 4px 24px rgba(0,0,0,0.12)",
      }}>
        <div style={{ textAlign: "center", marginBottom: "1.5rem" }}>
          <div style={{ fontSize: "2rem", marginBottom: "0.25rem" }}>AI Career Studio</div>
          <div style={{ color: "var(--color-text-muted)", fontSize: "0.875rem" }}>
            Your intelligent resume & career platform
          </div>
        </div>

        {/* Tabs */}
        <div style={{
          display: "flex",
          borderBottom: "2px solid var(--color-border)",
          marginBottom: "1.5rem",
        }}>
          {(["login", "register"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => { setTab(t); setError(""); }}
              style={{
                flex: 1,
                padding: "0.6rem",
                background: "none",
                border: "none",
                borderBottom: tab === t ? "2px solid var(--color-accent)" : "2px solid transparent",
                color: tab === t ? "var(--color-accent)" : "var(--color-text-muted)",
                fontWeight: tab === t ? 600 : 400,
                cursor: "pointer",
                fontSize: "0.95rem",
                marginBottom: "-2px",
                textTransform: "capitalize",
              }}
            >
              {t === "login" ? "Sign In" : "Create Account"}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "1rem" }}>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem", color: "var(--color-text-muted)" }}>
              Username
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter username"
              required
              autoFocus
              style={{
                width: "100%",
                padding: "0.6rem 0.75rem",
                borderRadius: "6px",
                border: "1px solid var(--color-border)",
                background: "var(--color-bg)",
                color: "var(--color-text)",
                fontSize: "0.95rem",
                boxSizing: "border-box",
              }}
            />
          </div>

          {tab === "register" && (
            <div style={{ marginBottom: "1rem" }}>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem", color: "var(--color-text-muted)" }}>
                Email (optional)
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                style={{
                  width: "100%",
                  padding: "0.6rem 0.75rem",
                  borderRadius: "6px",
                  border: "1px solid var(--color-border)",
                  background: "var(--color-bg)",
                  color: "var(--color-text)",
                  fontSize: "0.95rem",
                  boxSizing: "border-box",
                }}
              />
            </div>
          )}

          <div style={{ marginBottom: "1.25rem" }}>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem", color: "var(--color-text-muted)" }}>
              Password {tab === "register" && <span style={{ fontWeight: 400 }}>(min 6 chars)</span>}
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              required
              minLength={6}
              style={{
                width: "100%",
                padding: "0.6rem 0.75rem",
                borderRadius: "6px",
                border: "1px solid var(--color-border)",
                background: "var(--color-bg)",
                color: "var(--color-text)",
                fontSize: "0.95rem",
                boxSizing: "border-box",
              }}
            />
          </div>

          {error && (
            <div style={{
              marginBottom: "1rem",
              padding: "0.6rem 0.75rem",
              borderRadius: "6px",
              background: "rgba(220, 53, 69, 0.1)",
              border: "1px solid rgba(220, 53, 69, 0.3)",
              color: "#dc3545",
              fontSize: "0.875rem",
            }}>
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            style={{
              width: "100%",
              padding: "0.75rem",
              borderRadius: "6px",
              border: "none",
              background: "var(--color-accent)",
              color: "#fff",
              fontWeight: 600,
              fontSize: "1rem",
              cursor: loading ? "not-allowed" : "pointer",
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? "Please wait…" : tab === "login" ? "Sign In" : "Create Account"}
          </button>
        </form>

        <div style={{ textAlign: "center", marginTop: "1.25rem" }}>
          <button
            onClick={onGuest}
            style={{
              background: "none",
              border: "none",
              color: "var(--color-text-muted)",
              fontSize: "0.85rem",
              cursor: "pointer",
              textDecoration: "underline",
            }}
          >
            Continue as guest (no account)
          </button>
        </div>
      </div>
    </div>
  );
}
