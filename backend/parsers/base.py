from dataclasses import dataclass, field
from models import Profile


@dataclass
class ParseResult:
    profile: Profile
    warnings: list[str] = field(default_factory=list)
