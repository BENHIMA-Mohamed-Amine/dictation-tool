import json
import os
from pathlib import Path
from typing import Optional

import keyring
from dotenv import load_dotenv

load_dotenv()

CONFIG_DIR = Path.home() / ".config" / "dictation-tool"
KEYRING_SERVICE = "dictation-tool"

DEFAULTS = {
    "selected_provider": "groq",
    "keyterms": [],
}

ENV_KEY_VARS = {
    "groq": "GROQ_API_KEY",
    "soniox": "SONIOX_API_KEY",
    "nvidia": "NVIDIA_API_KEY",
}


class ConfigStore:
    def __init__(self, config_dir: Path = CONFIG_DIR) -> None:
        self.config_dir = config_dir
        self.config_file = config_dir / "config.json"

    def load(self) -> dict:
        if not self.config_file.exists():
            return dict(DEFAULTS)
        data = json.loads(self.config_file.read_text())
        return {**DEFAULTS, **data}

    def save(self, data: dict) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file.write_text(json.dumps(data, indent=2))

    def get_key(self, provider: str) -> Optional[str]:
        key = keyring.get_password(KEYRING_SERVICE, provider)
        if key:
            return key
        return os.environ.get(ENV_KEY_VARS.get(provider, ""))

    def set_key(self, provider: str, value: str) -> None:
        keyring.set_password(KEYRING_SERVICE, provider, value)
