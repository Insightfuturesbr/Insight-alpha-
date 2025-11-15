from __future__ import annotations

from flask import Blueprint, jsonify, request, session

from services.unified.master import run_all


bp = Blueprint("api_orchestrator", __name__, url_prefix="/api")


@bp.route("/backtest/run", methods=["POST"])
def api_run_backtest():
    temp_path = session.get("temp_path")
    if not temp_path:
        return jsonify({"status": "erro", "mensagem": "Nenhum arquivo processado na sessão."}), 400

    try:
        payload = request.get_json(force=True) or {}
        result = run_all(payload, temp_path=temp_path)
        return jsonify({"status": "ok", **result}), 200
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

