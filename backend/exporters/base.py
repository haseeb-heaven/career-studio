import re
from abc import ABC, abstractmethod
from models import Profile


class Exporter(ABC):
    mime_type: str = "application/octet-stream"
    extension: str = "bin"

    @abstractmethod
    def export(self, profile: Profile) -> bytes:
        ...

    def filename(self, profile: Profile) -> str:
        name = re.sub(r"[^\w\-]", "_", profile.full_name).strip("_") or "profile"
        return f"{name}.{self.extension}"
