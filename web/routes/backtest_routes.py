
from flask import Blueprint, session, request, jsonify
import pandas as pd
import logging

bp = Blueprint("backtest_routes", __name__)

@bp.route('/rodar_backtest', methods=['POST'])
def rodar_backtest():
    from services.logic.backtest import executar_backtest_completo,  gerar_frase_insight
    import os

    try:
        req = request.get_json()
        parametros_usuario = {
            "ativacao_percentual": float(req['ativacao_percentual']),
            "ativacao_base": req['ativacao_base'],
            "comparador_ativacao": req['comparador_ativacao'],
            "pausa_percentual": float(req['pausa_percentual']),
            "pausa_base": req['pausa_base'],
            "comparador_pausa": req['comparador_pausa'],
            "desativacao_percentual": float(req['desativacao_percentual']),
            "desativacao_base": req['desativacao_base'],
            "comparador_desativacao": req['comparador_desativacao'],
        }


        temp_path = session.get("temp_path", "")
        df_prebacktest = pd.read_json(os.path.join(temp_path, "prebacktest.json"), orient="split")


        df_backtest_recalculado, metricasback, metricas_original, df_comparativo = executar_backtest_completo(
            df_prebacktest, parametros_usuario, temp_path=temp_path, salvar_resultados=True
        )
        from services.utils.formatters import converter_valores_json_serializaveis
        session['metricasback'] = converter_valores_json_serializaveis(metricasback)
        session['metricas_original'] = converter_valores_json_serializaveis(metricas_original)

        ultima_linha = df_backtest_recalculado.iloc[-1].to_dict() if not df_backtest_recalculado.empty else {}

        # 🚀 Mapeamento para o Dr. Drawdown
        parametros_insight = {
            "ativar_percentual": parametros_usuario.get('ativacao_percentual', 0),
            "base_drawdown_ativar": parametros_usuario.get('ativacao_base', "Média dos Drawdowns"),
            "pausar_percentual": parametros_usuario.get('pausa_percentual', 0),
            "base_lucro_pausar": parametros_usuario.get('pausa_base', "Média dos Lucros"),
            "desativar_percentual": parametros_usuario.get('desativacao_percentual', 0),
            "base_drawdown_desativar": parametros_usuario.get('desativacao_base', "Maior Drawdown Histórico")
        }
        logging.debug("%s", parametros_insight)
        frase_dr_drawdown = gerar_frase_insight(parametros_insight, {
            "drawdown_maximo_simulado": metricasback['drawdown_maximo'],
            "meta_lucro_simulado": metricasback['soma_lucro_gerado']
        })
        retorno = {
            "status": "ok",
            "metricasback": converter_valores_json_serializaveis(metricasback),
            "metricasoriginal": converter_valores_json_serializaveis(metricas_original),
            "ultima_linha": converter_valores_json_serializaveis(ultima_linha),
            "frase_dr_drawdown": frase_dr_drawdown
        }


        logging.debug("%s", retorno)
        return jsonify(retorno)



    except Exception as e:
        logging.error("❌ Erro no backtest: %s", e)
        return jsonify({"status": "erro", "mensagem": str(e)}), 500

# Renomeado para evitar conflito com api/routes/api_comparativo.py
@bp.route("/api/comparativo/session", methods=["GET"])
def get_comparativo():
    import os
    import json

    temp_path = session.get("temp_path", "")
    caminho = os.path.join(temp_path, "comparativo_ciclos.json")

    if not os.path.exists(caminho):
        return jsonify({"erro": "Arquivo de comparativo não encontrado."}), 404

    with open(caminho, "r", encoding="utf-8") as f:
        comparativo = json.load(f)

    return jsonify(comparativo)
