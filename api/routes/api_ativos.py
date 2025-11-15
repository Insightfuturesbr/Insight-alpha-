from flask import Blueprint, jsonify, session
import os
from services.utils.file_io import carregar_json
import logging

bp = Blueprint("api_ativos", __name__, url_prefix="/api")

@bp.route("/ativos", methods=["GET"])
def get_ativos():
    temp_path = session.get("temp_path")
    if not temp_path:
        return jsonify({
            "status": "erro",
            "mensagem": "Nenhum arquivo foi processado ainda. Faça upload de uma planilha primeiro."
        }), 400

    arquivos_necessarios = ["ativos.json", "ativo.json", "parametros_ativo.json"]

    for nome in arquivos_necessarios:
        caminho = os.path.join(temp_path, nome)
        if not os.path.exists(caminho):
            return jsonify({
                "status": "erro",
                "mensagem": f"Arquivo {nome} não encontrado. Verifique o processamento do upload."
            }), 404

    ativo = carregar_json(temp_path, "ativo.json")
    ativos = carregar_json(temp_path, "ativos.json")
    parametros = carregar_json(temp_path, "parametros_ativo.json")

    logging.info("📥 Ativos carregados de: %s", temp_path)
    logging.debug("📘 Ativos: %s", ativos)
    logging.debug("🛠️ Parâmetros do Ativo: %s", parametros)

    return jsonify({
        "status": "ok",
        "ativo": ativo,
        "ativos": ativos,
        "parametros_ativo": parametros
    })
