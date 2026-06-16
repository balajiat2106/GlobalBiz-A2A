import os
from pathlib import Path


def load_env():
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return

    with env_path.open(encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")

            if key and key not in os.environ:
                os.environ[key] = value
