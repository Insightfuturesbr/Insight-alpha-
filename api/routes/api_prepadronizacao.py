from flask import Blueprint, jsonify, session
import os
from services.utils.file_io import carregar_json
import logging

bp = Blueprint("api_prepadronizacao", __name__, url_prefix="/api")

@bp.route("/prepadronizacao", methods=["GET"])
def get_prepadronizacao():
    temp_path = session.get("temp_path")
    if not temp_path:
        return jsonify({
            "status": "erro",
            "mensagem": "Nenhum arquivo foi processado ainda. Faça upload de uma planilha primeiro."
        }), 400

    # Verificação manual da existência dos arquivos
    caminho_pre = os.path.join(temp_path, "variaveis_pre.json")
    caminho_stats = os.path.join(temp_path, "estatisticas_positivas_negativas.json")

    if not os.path.exists(caminho_pre) or not os.path.exists(caminho_stats):
        return jsonify({
            "status": "erro",
            "mensagem": "Arquivos necessários não encontrados. Verifique o processamento do upload."
        }), 404

    # Carregamento correto com 2 argumentos
    dados_pre = carregar_json(temp_path, "variaveis_pre.json")
    dados_stats = carregar_json(temp_path, "estatisticas_positivas_negativas.json")

    logging.info("📥 Carregando de: %s", temp_path)
    logging.debug("📥 Dados lidos: %s", dados_pre)

    return jsonify({
        "status": "ok",
        "variaveis_pre": dados_pre,
        "estatisticas_positivas_negativas": dados_stats
    })
