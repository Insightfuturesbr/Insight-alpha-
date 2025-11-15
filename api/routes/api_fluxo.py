from flask import Blueprint, jsonify, session
from services.utils.file_io import carregar_json

bp = Blueprint("api_fluxo", __name__, url_prefix="/api")

@bp.route("/fluxo", methods=["GET"])
def get_fluxo():
    temp_path = session.get("temp_path", None)

    if not temp_path:
        return jsonify({
            "status": "erro",
            "mensagem": "Sessão não iniciada. Faça o upload de um arquivo para começar a análise."
        }), 400

    dados_fluxo = carregar_json(temp_path, "variaveis_fluxo.json")
    dados_resultados = carregar_json(temp_path, "resultados_fluxo_ciclo.json")

    return jsonify({
        "status": "ok",
        "variaveis_fluxo": dados_fluxo,
        "resultados_fluxo_ciclo": dados_resultados
    })
