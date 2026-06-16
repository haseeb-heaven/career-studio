import { useState, useEffect } from "react";
import type { AuthUser } from "../types";
import { register, login, setAuthToken, forgotPassword, resetPassword } from "../api";

interface Props {
  onAuth: (user: AuthUser) => void;
  onGuest: () => void;
}

type Tab = "login" | "register" | "forgot" | "reset";

export default function LoginScreen({ onAuth, onGuest }: Props) {
  const [tab, setTab] = useState<Tab>("login");
  const [resetToken, setResetToken] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [email, setEmail] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [successMsg, setSuccessMsg] = useState("");
  const [devResetUrl, setDevResetUrl] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const token = params.get("token");
    if (token) {
      setResetToken(token);
      setTab("reset");
    }
  }, []);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSuccessMsg("");
    setLoading(true);
    try {
      let result;
      if (tab === "forgot") {
        const res = await forgotPassword(username.trim());
        setSuccessMsg(res.message);
        if (res.dev_reset_url) setDevResetUrl(res.dev_reset_url);
        return;
      } else if (tab === "reset") {
        const res = await resetPassword(resetToken, password);
        setSuccessMsg(res.message);
        setTimeout(() => {
          window.history.replaceState({}, document.title, "/");
          setTab("login");
          setPassword("");
          setSuccessMsg("");
        }, 2000);
        return;
      } else if (tab === "register") {
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
        {tab !== "reset" && tab !== "forgot" && (
        <div style={{
          display: "flex",
          borderBottom: "2px solid var(--color-border)",
          marginBottom: "1.5rem",
        }}>
          {(["login", "register"] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => { setTab(t); setError(""); setSuccessMsg(""); setDevResetUrl(""); }}
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
        )}

        {tab === "forgot" && (
          <div style={{ textAlign: "center", marginBottom: "1.5rem" }}>
            <h2 style={{ fontSize: "1.2rem", marginBottom: "0.5rem" }}>Reset Password</h2>
            <p style={{ fontSize: "0.9rem", color: "var(--color-text-muted)" }}>
              Enter your username and we'll send a reset link to your registered email address.
            </p>
          </div>
        )}

        {tab === "reset" && (
          <div style={{ textAlign: "center", marginBottom: "1.5rem" }}>
            <h2 style={{ fontSize: "1.2rem", marginBottom: "0.5rem" }}>Set New Password</h2>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          {tab !== "reset" && (
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
          )}

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

          {tab !== "forgot" && (
          <div style={{ marginBottom: "1.25rem" }}>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 600, marginBottom: "0.3rem", color: "var(--color-text-muted)" }}>
              {tab === "reset" ? "New Password" : "Password"} {tab === "register" && <span style={{ fontWeight: 400 }}>(min 6 chars)</span>}
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
          )}

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

          {successMsg && (
            <div style={{
              marginBottom: "1rem",
              padding: "0.6rem 0.75rem",
              borderRadius: "6px",
              background: "rgba(40, 167, 69, 0.1)",
              border: "1px solid rgba(40, 167, 69, 0.3)",
              color: "#28a745",
              fontSize: "0.875rem",
            }}>
              {successMsg}
              {devResetUrl && (
                <div style={{ marginTop: "0.5rem" }}>
                  <a
                    href={devResetUrl}
                    style={{ color: "#28a745", fontWeight: 600, wordBreak: "break-all" }}
                  >
                    Click here to reset your password →
                  </a>
                </div>
              )}
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
            {loading ? "Please wait…" : tab === "login" ? "Sign In" : tab === "register" ? "Create Account" : tab === "forgot" ? "Send Reset Link" : "Reset Password"}
          </button>
        </form>

        <div style={{ textAlign: "center", marginTop: "1.25rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {tab === "login" && (
            <button
              type="button"
              onClick={() => { setTab("forgot"); setError(""); setSuccessMsg(""); setDevResetUrl(""); }}
              style={{
                background: "none",
                border: "none",
                color: "var(--color-accent)",
                fontSize: "0.85rem",
                cursor: "pointer",
              }}
            >
              Forgot Password?
            </button>
          )}
          {(tab === "forgot" || tab === "reset") && (
            <button
              type="button"
              onClick={() => { setTab("login"); setError(""); setSuccessMsg(""); setDevResetUrl(""); }}
              style={{
                background: "none",
                border: "none",
                color: "var(--color-text-muted)",
                fontSize: "0.85rem",
                cursor: "pointer",
                textDecoration: "underline",
              }}
            >
              Back to Sign In
            </button>
          )}
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
