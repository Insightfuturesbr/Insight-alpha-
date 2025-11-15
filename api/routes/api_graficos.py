# api/routes/api_graficos.py

from flask import Blueprint, jsonify, session
from services.utils.file_io import carregar_json
from visual.graficos_plotly import ( gerar_grafico_ciclos_lucro,
                                    gerar_grafico_divida_acumulada_simulada,
                                    gerar_grafico_pizza,
                                    gerar_grafico_ciclos_drawdown_e_lucro,
                                    gerar_grafico_barras_horizontais_operacoes)
import pandas as pd
import logging
import json
from plotly.utils import PlotlyJSONEncoder

def _compat_payload(fig_dict: dict, legacy_key: str) -> dict:
    """Retorna tanto o formato novo (figure=dict) quanto o legado (string)."""
    fig_json = json.dumps(fig_dict, cls=PlotlyJSONEncoder)
    return {"status": "ok", legacy_key: fig_json, "figure": fig_dict}

bp = Blueprint("api_graficos", __name__, url_prefix="/api")



@bp.route("/graficos/padronizacao", methods=["GET"])
def graficos_padronizacao():
    temp_path = session.get("temp_path")
    if not temp_path:
        return jsonify({"status": "erro", "mensagem": "Nenhum arquivo foi enviado."}), 400

    try:
        # 🔹 Dados estatísticos das operações
        stats = carregar_json(temp_path, "estatisticas_positivas_negativas.json")
        fluxo = carregar_json(temp_path, "variaveis_fluxo.json")

        # Gráfico de barras com distribuição das operações
        fig1 = gerar_grafico_barras_horizontais_operacoes(
            positivas=stats.get("qtd_positivas", 0),
            negativas=stats.get("qtd_negativas", 0),
            neutras=stats.get("qtd_neutras", 0)
        )

        # Gráfico pizza de valores (empréstimos, amortizações, lucros)
        fig2 = gerar_grafico_pizza(
            emprestimos=fluxo.get("valor_emprestado", 0),
            amortizacoes=fluxo.get("amortizacao", 0),
            lucros=fluxo.get("lucro_gerado", 0),
            labels=["Empréstimos", "Amortizações", "Lucros"]
        )

        # Gráfico pizza de quantidades de operações
        fig3 = gerar_grafico_pizza(
            emprestimos=fluxo.get("qtde_emprestado", 0),
            amortizacoes=fluxo.get("qtde_amortizacao", 0),
            lucros=fluxo.get("qtde_lucro", 0),
            labels=["Qtde Empréstimos", "Qtde Amortizações", "Qtde Lucros"]
        )

        return jsonify({
            "status": "ok",
            "barras_operacoes": fig1,
            "pizza_valores": fig2,
            "pizza_qtde": fig3
        })

    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@bp.route("/graficos/drawdown", methods=["GET"])
def graficos_drawdown():
    temp_path = session.get("temp_path")
    if not temp_path:
        return jsonify({"status": "erro", "mensagem": "Nenhum arquivo foi enviado."}), 400

    try:
        # Carrega arquivos, permitindo que estejam ausentes
        df_drawdown = carregar_json(temp_path, "resumo_ciclos_divida.json") or []
        df_lucro = carregar_json(temp_path, "resultados_ciclos_lucro.json") or []
        stats_lucro = carregar_json(temp_path, "estatisticas_ciclos_lucro.json") or {}
        df_completo = carregar_json(temp_path, "resultados_completos.json") or []

        # segurança extra — converte listas/dicts vazios em DataFrames vazios
        def _to_df(obj):
            try:
                if isinstance(obj, (list, dict)):
                    return pd.DataFrame(obj)
                if isinstance(obj, pd.DataFrame):
                    return obj
            except Exception:
                pass
            return pd.DataFrame()

        df_drawdown = _to_df(df_drawdown)
        df_lucro = _to_df(df_lucro)

        if df_drawdown.empty and df_lucro.empty:
            return jsonify({
                "status": "ok",
                "mensagem": "Ainda não há dados suficientes para o gráfico de drawdown.",
                "grafico_ciclos": None
            }), 200

        grafico_json = gerar_grafico_ciclos_drawdown_e_lucro(df_drawdown, df_lucro, stats_lucro)

        return jsonify({
            "status": "ok",
            "grafico_ciclos": grafico_json
        }), 200

    except FileNotFoundError:
        return jsonify({
            "status": "ok",
            "mensagem": "Arquivos de drawdown/lucro ainda não foram gerados.",
            "grafico_ciclos": None
        }), 200

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            "status": "erro",
            "mensagem": f"Erro ao gerar gráfico de drawdown: {e}"
        }), 500


@bp.route("/graficos/lucro", methods=["GET"])
def grafico_ciclos_lucro():
    temp_path = session.get("temp_path")
    if not temp_path:
        return jsonify({"status": "erro", "mensagem": "Nenhum arquivo foi enviado."}), 400

    try:
        df_lucros = carregar_json(temp_path, "resultados_ciclos_lucro.json")
        df_drawdown = carregar_json(temp_path, "resumo_ciclos_divida.json")

        grafico = gerar_grafico_ciclos_lucro(df_lucros, df_drawdown)

        return jsonify({"status": "ok", "grafico_lucro": grafico})
    except Exception as e:
        return jsonify({"status": "erro", "mensagem": str(e)}), 500


@bp.route("/graficos/divida", methods=["GET"])
def grafico_divida_acumulada():
    temp_path = session.get("temp_path")
    if not temp_path:
        return jsonify({"status": "erro", "mensagem": "Nenhum arquivo foi enviado."}), 400

    try:
        # 📊 Carrega o ciclo completo para o eixo x e y do gráfico
        df_ultimo_ciclo = pd.DataFrame(carregar_json(temp_path, "ultimo_ciclo_completo.json"))
        df_drawdown = carregar_json(temp_path, "resumo_ciclos_divida.json")
        df_ultimo_ciclo["Abertura"] = pd.to_datetime(df_ultimo_ciclo["Abertura"], errors="coerce")
        df_ultimo_ciclo["Dívida Acumulada"] = pd.to_numeric(df_ultimo_ciclo["Dívida Acumulada"], errors="coerce")
        logging.debug(df_ultimo_ciclo[["Abertura", "Dívida Acumulada"]].tail())
        logging.debug(df_ultimo_ciclo.dtypes)
        logging.debug(df_ultimo_ciclo.columns.tolist())

        # 📥 Carrega as estatísticas do último ciclo (métricas fixas para linhas horizontais)
        estatisticas = carregar_json(temp_path, "ultimo_ciclo.json")
        media = estatisticas.get("Média Máximas Até o Ciclo", 0)
        percentil25 = estatisticas.get("Percentil 75 Máximas Até o Ciclo", 0)
        minima = df_drawdown.get("Máxima Dívida do Ciclo", 0)
        logging.info("Média: %s", media)
        logging.info("Percentil 25: %s", percentil25)
        logging.info("Mínima: %s", minima)

        # 📈 Gera o gráfico
        grafico = gerar_grafico_divida_acumulada_simulada(
            df_simulado=df_ultimo_ciclo[["Abertura", "Dívida Acumulada"]],
            media=media,
            percentil25=percentil25,
            minima=minima
        )

        return jsonify({"status": "ok", "grafico_divida": grafico})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"status": "erro", "mensagem": str(e)}), 500
