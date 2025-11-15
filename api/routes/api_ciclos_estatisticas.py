from flask import Blueprint, jsonify, session
from services.utils.file_io import carregar_json

bp = Blueprint("api_ciclos_estatisticas", __name__, url_prefix="/api")

@bp.route("/ciclos/estatisticas", methods=["GET"])
def get_estatisticas_ciclos():
    temp_path = session.get("temp_path", None)

    if not temp_path:
        return jsonify({
            "status": "erro",
            "mensagem": "Nenhum arquivo foi carregado na sessão."
        }), 400

    arquivos = [
        "estatisticas_ciclo_emprestimo.json",
        "estatisticas_ciclo_amortizacao.json",
        "estatisticas_ciclo_lucro.json",
        "estats_qtd_emp_ciclo.json",
        "estats_qtd_amo_ciclo.json",
        "estats_qtd_luc_ciclo.json",
        "estatisticas_duracao_ciclos.json",
        "estatisticas_ciclos_lucro.json",

    ]

    estatisticas = {}

    for nome in arquivos:
        chave = nome.replace(".json", "")
        estatisticas[chave] = carregar_json(temp_path, nome, raise_if_missing=False, default={})

    return jsonify({
        "status": "ok",
        **estatisticas
    })
