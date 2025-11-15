from flask import Blueprint, jsonify, session
import os
from services.utils.file_io import carregar_json

bp = Blueprint("api_padronizacao", __name__, url_prefix="/api")

@bp.route("/padronizacao", methods=["GET"])
def get_padronizacao():
    temp_path = session.get("temp_path")
    if not temp_path:
        return jsonify({"status": "erro", "mensagem": "Arquivo não enviado"}), 400

    arquivo = "padronizacao.json"
    caminho = os.path.join(temp_path, arquivo)
    if not os.path.exists(caminho):
        return jsonify({"status": "erro", "mensagem": f"Arquivo {arquivo} não encontrado"}), 404

    dados = carregar_json(temp_path, arquivo)

    return jsonify({"status": "ok", "padronizacao": dados})
