from flask import Blueprint, jsonify, session
from services.utils.file_io import carregar_json

bp = Blueprint("api_insights", __name__, url_prefix="/api")

@bp.route("/insights", methods=["GET"])
def get_insights():
    temp_path = session.get("temp_path", None)

    if not temp_path:
        return jsonify({
            "status": "erro",
            "mensagem": "Nenhum arquivo foi carregado na sessão."
        }), 400

    ultimos_resultados = carregar_json(temp_path, "ultimo_ciclo_completo.json")
    ultimas_quantidades = carregar_json(temp_path, "ultimo_resultado.json")
    prebacktest = carregar_json(temp_path, "prebacktest.json")

    return jsonify({
        "status": "ok",
        "ultimos_resultados_periodo": ultimos_resultados,
        "ultimas_quantidades_periodo": ultimas_quantidades,
        "prebacktest": prebacktest
    })
