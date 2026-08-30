import json
import re
from pathlib import Path


PLUGIN_JSON = Path(__file__).resolve().parents[3] / ".codex-plugin" / "plugin.json"
_SEMVER_PATTERN = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


def get_skill_version() -> str:
    """Return the plugin version from the canonical metadata file."""
    try:
        with PLUGIN_JSON.open(encoding="utf-8") as metadata_file:
            metadata = json.load(metadata_file)
    except (OSError, json.JSONDecodeError, TypeError) as exc:
        raise ValueError("无法读取 Plugin 版本") from exc

    version = metadata.get("version") if isinstance(metadata, dict) else None
    if not isinstance(version, str) or not _SEMVER_PATTERN.fullmatch(version):
        raise ValueError("Plugin 版本必须是语义化版本 X.Y.Z")
    return version
