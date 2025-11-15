#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import secrets

ROOT = Path(__file__).resolve().parents[1]
env_path = ROOT / ".env"
example_path = ROOT / ".env.example"

def main() -> None:
    if env_path.exists():
        print(".env already exists; no changes made.")
        return

    secret = secrets.token_urlsafe(32)
    content = []

    if example_path.exists():
        # Start from example; replace or insert SECRET_KEY
        lines = example_path.read_text().splitlines()
        saw_secret = False
        for line in lines:
            if line.strip().startswith("SECRET_KEY="):
                content.append(f"SECRET_KEY={secret}")
                saw_secret = True
            else:
                content.append(line)
        if not saw_secret:
            content.append(f"SECRET_KEY={secret}")
    else:
        # Minimal .env
        content = [
            "ENV=production",
            "FLASK_ENV=production",
            f"SECRET_KEY={secret}",
            "# DATABASE_URL=sqlite:////app/dev.db",
        ]

    env_path.write_text("\n".join(content) + "\n")
    # Restrict perms
    try:
        os.chmod(env_path, 0o600)
    except Exception:
        pass
    print("Created .env with generated SECRET_KEY")

if __name__ == "__main__":
    main()

