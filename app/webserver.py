from __future__ import annotations

from flask import Flask, session
from flask.json.provider import DefaultJSONProvider
from pathlib import Path

from app.core.config import settings
from app.core.paths import UPLOAD_FOLDER, OUTPUTS_DIR
from app.core.logging import init_logging
from app.core.error_handlers import register_error_handlers

# Blueprints existentes
from web.routes.auth_routes import bp as auth_bp
from web.routes.upload_routes import bp as upload_bp
from web.routes.painel_routes import painel_routes as painel_bp
from web.routes.backtest_routes import bp as backtest_bp
from web.routes.contratos_routes import bp as contratos_bp
from web.routes.api_routes import bp as api_bp
from web.routes.public_routes import bp as public_bp
from api.routes.api_strategies import bp as api_strategies_bp


class IFJSONProvider(DefaultJSONProvider):
    def default(self, o):
        if isinstance(o, Path):
            return str(o)
        return super().default(o)


def create_app() -> Flask:
    init_logging()

    app = Flask(
        __name__,
        template_folder=settings.templates_dir,  # já string
        static_folder=settings.static_dir,      # já string
    )
    app.json = IFJSONProvider(app)  # ✅ JSON aceita Path
    app.secret_key = settings.SECRET_KEY

    app.config["ENV"] = settings.ENV
    app.config["TEMPLATES_AUTO_RELOAD"] = settings.ENV != "production"

    # diretórios como string (seguro pra sessão/JSON)
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
    app.config["OUTPUTS_DIR"] = OUTPUTS_DIR

    # Blueprints (ordem: público → auth → upload → painel → APIs)
    app.register_blueprint(public_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(painel_bp)
    app.register_blueprint(backtest_bp)
    app.register_blueprint(contratos_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(api_strategies_bp)

    # Healthcheck
    @app.get("/health")
    def health():
        return {"status": "ok", "env": settings.ENV}, 200
    # ✅ registrar handlers de erro
    register_error_handlers(app)
    # Sanitiza qualquer Path que tenha ido parar na sessão
    @app.after_request
    def _sanitize_session(response):
        convert = {}
        for k, v in list(session.items()):
            if isinstance(v, Path):
                convert[k] = str(v)
            elif isinstance(v, (list, tuple)):
                new_v = [str(x) if isinstance(x, Path) else x for x in v]
                if new_v != list(v):
                    convert[k] = new_v if isinstance(v, list) else tuple(new_v)
            elif isinstance(v, dict):
                new_v = {kk: (str(vv) if isinstance(vv, Path) else vv) for kk, vv in v.items()}
                if new_v != v:
                    convert[k] = new_v
        for k, v in convert.items():
            session[k] = v
        return response
        # 🔎 debug opcional (só em dev): visualizar sessão
    if app.config["ENV"] != "production":
            @app.get("/__session_debug__")
            def __session_debug__():
                types = {k: type(v).__name__ for k, v in session.items()}
                return {"items": {k: str(v) for k, v in session.items()}, "types": types}, 200


    return app