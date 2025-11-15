#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.getcwd())

from app.webserver import create_app  # noqa: E402


def main() -> int:
    app = create_app()
    with app.test_client() as client:
        resp = client.get("/health")
        print("STATUS:", resp.status)
        try:
            data = resp.get_json()
        except Exception:
            data = resp.data.decode("utf-8", errors="replace")
        print("BODY:")
        print(json.dumps(data, indent=2) if isinstance(data, dict) else data)
        return 0 if resp.status_code == 200 else 1


if __name__ == "__main__":
    raise SystemExit(main())

