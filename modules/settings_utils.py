# modules/settings_utils.py
from pathlib import Path
import json

APP_DIR = Path(__file__).resolve().parent.parent
CFG_DIR = APP_DIR / "config"
CFG_DIR.mkdir(exist_ok=True)
CFG_PATH = CFG_DIR / "settings.json"

# Default weights match your config.yaml keys
DEFAULT_SETTINGS = {
    "weights": {
        "skills": 0.60,
        "experience": 0.25,
        "education": 0.15,
        "embedding": 0.00
    }
}

def load_settings():
    if CFG_PATH.exists():
        return json.loads(CFG_PATH.read_text())
    save_settings(DEFAULT_SETTINGS)
    return DEFAULT_SETTINGS

def save_settings(cfg: dict):
    CFG_PATH.write_text(json.dumps(cfg, indent=2))

def normalize_weights(w: dict):
    total = sum(max(v, 0) for v in w.values())
    return {k: (max(v, 0) / total if total > 0 else 0) for k, v in w.items()}
