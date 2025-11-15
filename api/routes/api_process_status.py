from __future__ import annotations
from flask import Blueprint, jsonify, session
import os

bp = Blueprint("api_process_status", __name__, url_prefix="/api")

# ✅ liste aqui os JSONs mínimos que sua(s) página(s) consomem
REQUIRED_FILES = [
    "ativo.json",
    "ativos.json",
    "parametros_ativo.json",
    "estatisticas_ciclo_emprestimo.json",
    "estatisticas_ciclo_amortizacao.json",
    "estatisticas_ciclo_lucro.json",
    "estats_qtd_emp_ciclo.json",
    "estats_qtd_amo_ciclo.json",
    "estats_qtd_luc_ciclo.json",
    "padronizacao.json",
    "resultados_fluxo_ciclo.json",

]

@bp.get("/ready")
def ready():
    temp_path = session.get("temp_path")
    if not temp_path:
        return jsonify({"ready": False, "reason": "no_temp_path"}), 200

    lock_file = os.path.join(temp_path, ".processing.lock")
    missing = [f for f in REQUIRED_FILES if not os.path.exists(os.path.join(temp_path, f))]
    locked = os.path.exists(lock_file)
    ready = (not locked) and (len(missing) == 0)

    return jsonify({
        "ready": ready,
        "locked": locked,
        "missing": missing,
        "temp_path": temp_path,
    }), 200
