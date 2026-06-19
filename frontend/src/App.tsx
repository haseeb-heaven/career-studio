import { useState, useEffect } from "react";
import type { AuthUser } from "./types";
import UploadScreen from "./components/UploadScreen";
import ProfileEditor from "./components/ProfileEditor";
import LoginScreen from "./components/LoginScreen";
import { ToastProvider } from "./components/Toast";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { setAuthToken, verifyToken } from "./api";
import type { Profile } from "./types";

type Screen = "login" | "upload" | "editor";

export default function App() {
  const [screen, setScreen] = useState<Screen>("login");
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [profileId, setProfileId] = useState<number | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [authChecked, setAuthChecked] = useState(false);
  const [prefetchedProfile, setPrefetchedProfile] = useState<Profile | null>(null);

  // Restore session from localStorage on mount
  useEffect(() => {
    const token = localStorage.getItem("auth_token");
    if (token) {
      setAuthToken(token);
      verifyToken().then((user) => {
        if (user) {
          setAuthUser(user);
          setScreen("upload");
        } else {
          // Token expired or invalid
          localStorage.removeItem("auth_token");
          localStorage.removeItem("auth_user");
          setAuthToken(null);
        }
        setAuthChecked(true);
      });
    } else {
      setAuthChecked(true);
    }
  }, []);

  function handleAuth(user: AuthUser) {
    setAuthUser(user);
    setScreen("upload");
  }

  function handleGuest() {
    setAuthToken(null);
    setAuthUser(null);
    setScreen("upload");
  }

  function handleLogout() {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("auth_user");
    setAuthToken(null);
    setAuthUser(null);
    setProfileId(null);
    setWarnings([]);
    setScreen("login");
  }

  function handleImported(id: number, w: string[], prefetched?: Profile | null) {
    setProfileId(id);
    setWarnings(w);
    setPrefetchedProfile(prefetched ?? null);
    setScreen("editor");
  }

  if (!authChecked) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ color: "var(--color-text-muted)" }}>Loading…</span>
      </div>
    );
  }

  return (
    <ToastProvider>
      {screen === "login" ? (
        <LoginScreen onAuth={handleAuth} onGuest={handleGuest} />
      ) : screen === "upload" ? (
        <UploadScreen
          onImported={handleImported}
          authUser={authUser}
          onLogout={handleLogout}
        />
      ) : (
        <ErrorBoundary>
          <ProfileEditor
            profileId={profileId!}
            importWarnings={warnings}
            authUser={authUser}
            onLogout={handleLogout}
            prefetchedProfile={prefetchedProfile}
            onBack={() => {
              setScreen("upload");
              setWarnings([]);
              setProfileId(null);
              setPrefetchedProfile(null);
            }}
          />
        </ErrorBoundary>
      )}
    </ToastProvider>
  );
}
