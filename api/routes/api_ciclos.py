# api/routes/api_ciclos.py

from flask import Blueprint, jsonify, session
import os
from services.utils.file_io import carregar_json
import logging

bp = Blueprint("api_ciclos", __name__, url_prefix="/api")

@bp.route("/ciclos", methods=["GET"])
def get_ciclos():
    temp_path = session.get("temp_path")

    if not temp_path:
        return jsonify({
            "status": "erro",
            "mensagem": "Sessão não encontrada. Faça o upload de um arquivo para iniciar a análise."
        }), 400

    arquivos = {
        "resumo_ciclos_divida": "resumo_ciclos_divida.json",
        "ultimo_ciclo": "ultimo_ciclo.json",
        "ultimo_ciclo_completo": "ultimo_ciclo_completo.json",
        "ciclos_lucro": "resultados_ciclos_lucro.json",
        "resumo_ciclos_lucro": "estatisticas_ciclos_lucro.json",
        "estatisticas_duracao_ciclos": "estatisticas_duracao_ciclos.json"
    }

    resposta = {"status": "ok"}

    for chave, nome_arquivo in arquivos.items():
        if os.path.exists(os.path.join(temp_path, nome_arquivo)):
            resposta[chave] = carregar_json(temp_path, nome_arquivo)
        else:
            resposta[chave] = None
            logging.warning("⚠️ Arquivo não encontrado: %s", os.path.join(temp_path, nome_arquivo))
    return jsonify(resposta)


