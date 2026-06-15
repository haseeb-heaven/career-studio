import { useState } from "react";
import UploadScreen from "./components/UploadScreen";
import ProfileEditor from "./components/ProfileEditor";
import { ToastProvider } from "./components/Toast";

type Screen = "upload" | "editor";

export default function App() {
  const [screen, setScreen] = useState<Screen>("upload");
  const [profileId, setProfileId] = useState<number | null>(null);
  const [warnings, setWarnings] = useState<string[]>([]);

  function handleImported(id: number, w: string[]) {
    setProfileId(id);
    setWarnings(w);
    setScreen("editor");
  }

  return (
    <ToastProvider>
      {screen === "upload" ? (
        <UploadScreen onImported={handleImported} />
      ) : (
        <ProfileEditor
          profileId={profileId!}
          importWarnings={warnings}
          onBack={() => {
            setScreen("upload");
            setWarnings([]);
            setProfileId(null);
          }}
        />
      )}
    </ToastProvider>
  );
}
