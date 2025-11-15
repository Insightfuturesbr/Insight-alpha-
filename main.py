# main.py
import os
from app.webserver import create_app


def main():
    # garante que, se não houver FLASK_ENV definido, caia em "development"
    os.environ.setdefault("FLASK_ENV", "development")

    app = create_app()

    # reload automático de templates em dev
    app.config["TEMPLATES_AUTO_RELOAD"] = True

    # roda em debug só se ENV estiver setado para "development"
    app.run(
        debug=(app.config.get("ENV") == "development"),
        host="127.0.0.1",
        port=5000
    )


if __name__ == "__main__":
    main()
