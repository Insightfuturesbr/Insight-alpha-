from __future__ import annotations

from app.webserver import create_app

# WSGI entrypoint for Gunicorn (no factory flag, no parentheses needed)
app = create_app()

