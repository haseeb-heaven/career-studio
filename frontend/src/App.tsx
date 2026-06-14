import { useState } from "react";
import UploadScreen from "./components/UploadScreen";
import WarningBanner from "./components/WarningBanner";
import ProfileEditor from "./components/ProfileEditor";

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

  if (screen === "upload") {
    return <UploadScreen onImported={handleImported} />;
  }

  return (
    <>
      {warnings.length > 0 && (
        <div className="fixed left-0 right-0 top-0 z-50 p-4">
          <WarningBanner warnings={warnings} />
        </div>
      )}
      <ProfileEditor
        profileId={profileId!}
        onBack={() => {
          setScreen("upload");
          setWarnings([]);
          setProfileId(null);
        }}
      />
    </>
  );
}
