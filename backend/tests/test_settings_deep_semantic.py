"""Unit tests for the use_deep_semantic_matching Settings field (hybrid semantic matching)."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from models import Settings
from routers.settings_router import ALLOWED


def test_settings_model_has_deep_semantic_field_default_false():
    s = Settings()
    assert s.use_deep_semantic_matching is False


def test_use_deep_semantic_matching_is_allowed_settings_key():
    assert "use_deep_semantic_matching" in ALLOWED
