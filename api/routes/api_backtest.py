# api/routes/api_backtest.py

from flask import Blueprint, jsonify, session
import os
from services.utils.file_io import carregar_json

bp = Blueprint("api_backtest", __name__, url_prefix="/api")

@bp.route("/backtest", methods=["GET"])
def get_backtest():
    temp_path = session.get("temp_path", None)
    if not temp_path:
        return jsonify({"status": "erro", "mensagem": "Nenhum arquivo processado."}), 400

    try:
        # Prefer namespaced files with fallback to root for compatibility
        bt_dir = os.path.join(temp_path, "backtest")
        metricas_backtest = carregar_json(bt_dir, "metricas_backtest.json", raise_if_missing=False)
        if metricas_backtest is None:
            metricas_backtest = carregar_json(temp_path, "metricas_backtest.json")

        metricas_original = carregar_json(bt_dir, "metricas_original.json", raise_if_missing=False)
        if metricas_original is None:
            metricas_original = carregar_json(temp_path, "metricas_original.json")

        return jsonify({
            "status": "ok",
            "metricas_backtest": metricas_backtest,
            "metricas_original": metricas_original
        })
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500
