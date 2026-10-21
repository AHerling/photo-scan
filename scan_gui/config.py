"""Persistent settings: last device, output directories, saved presets.

Stored as JSON in ~/.config/scan-gui/config.json. Tolerant by design:
a missing or corrupt file silently falls back to defaults.
"""

import json
from pathlib import Path

APP_CONFIG_DIR = Path.home() / ".config" / "scan-gui"
CONFIG_PATH = APP_CONFIG_DIR / "config.json"

DEFAULTS: dict = {
    "last_device": None,                       # device name from scanimage -L
    "raw_dir": str(Path.home() / "Scan" / "Raw"),
    "photo_dir": str(Path.home() / "Scan" / "Photo"),
    "presets": {},                             # M2: name -> {option: value}
}


def load_config() -> dict:
    cfg = dict(DEFAULTS)
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return cfg
    if isinstance(data, dict):
        cfg.update({key: value for key, value in data.items() if key in DEFAULTS})
    return cfg


def save_config(cfg: dict) -> None:
    APP_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
