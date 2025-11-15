import pandas as pd
from services.analysis.endividamento import formatar_duracao
import numpy as np
import re

def resumir_ciclos_lucro_real_backtest(df_ciclos_lucro: pd.DataFrame) -> dict:
    """
    Gera um resumo estatístico dos ciclos de lucro real:
    - Quantidade total
    - Maior lucro
    - Média dos lucros
    - Percentil 75
    - Último lucro registrado (ciclo atual)
    """

    if df_ciclos_lucro is None or df_ciclos_lucro.empty:
        return {
            "quantidade_ciclos_lucro": 0,
            "maior_lucro_ciclo": 0,
            "media_lucros": 0,
            "percentil_75_lucros": 0,
            "lucro_ciclo_atual": 0
        }

    lucros = df_ciclos_lucro["Lucro Gerado no Ciclo"].tolist()
    quantidade = len(lucros)
    maior = max(lucros)
    media = round(float(np.mean(lucros)), 2)
    perc75 = round(float(np.percentile(lucros, 75)), 2) if len(lucros) >= 2 else media
    atual = lucros[-1] if quantidade > 0 else 0

    resumo = {
        "quantidade_ciclos_lucro": quantidade,
        "maior_lucro_ciclo": round(maior, 2),
        "media_lucros": media,
        "percentil_75_lucros": perc75,
        "lucro_ciclo_atual": round(atual, 2)
    }

    return resumo

def gerar_resumo_e_dataframe_ciclos_lucro_backtest(df: pd.DataFrame):
    """
    Gera um resumo estatístico dos ciclos de lucro real com estrutura padronizada.
    Considera ciclos com 'Lucro Gerado' > 0 e 'Dívida Acumulada' == 0.

    Retorna:
        - resumo (list): lista de dicionários com dados por ciclo
        - df_resumo (DataFrame): DataFrame estruturado com colunas padronizadas
    """

    resumo = []
    maximos_anteriores = []

    em_lucro = False
    data_inicio, lucro_total, id_lucro_atual = None, 0, None

    for i, row in df.iterrows():
        lucro = row["Lucro Gerado"]
        divida = row["Dívida Acumulada"]
        id_op = row["ID Operação"]
        data = row.name

        # Extrai o ID do lucro no formato L123
        match = re.search(r'L(\d+)', id_op)
        id_lucro = int(match.group(1)) if match else None

        if lucro > 0 and divida == 0:
            if not em_lucro:
                # Novo ciclo
                data_inicio = data
                id_lucro_atual = id_lucro
                lucro_total = lucro
                em_lucro = True
            else:
                lucro_total += lucro
        else:
            if em_lucro:
                duracao = pd.to_datetime(data) - pd.to_datetime(data_inicio)
                media = float(np.mean(maximos_anteriores)) if maximos_anteriores else 0.0
                perc25 = float(np.percentile(maximos_anteriores, 25)) if len(maximos_anteriores) >= 2 else media

                resumo.append({
                    "ID Ciclo de Lucro": id_lucro_atual,
                    "Data Início": str(data_inicio),
                    "Data Fim": str(data),
                    "Duração do Ciclo": formatar_duracao(duracao),
                    "Lucro Gerado no Ciclo": round(lucro_total, 2),
                    "Média Lucros Até o Ciclo": round(media, 2),
                    "Percentil 25 Lucros Até o Ciclo": round(perc25, 2)
                })

                maximos_anteriores.append(lucro_total)
                em_lucro = False

    # Se terminou em um ciclo aberto
    if em_lucro:
        duracao = pd.to_datetime(data) - pd.to_datetime(data_inicio)
        media = float(np.mean(maximos_anteriores)) if maximos_anteriores else 0.0
        perc25 = float(np.percentile(maximos_anteriores, 25)) if len(maximos_anteriores) >= 2 else media

        resumo.append({
            "ID Ciclo de Lucro": id_lucro_atual,
            "Data Início": str(data_inicio),
            "Data Fim": str(data),
            "Duração do Ciclo": formatar_duracao(duracao),
            "Lucro Gerado no Ciclo": round(lucro_total, 2),
            "Média Lucros Até o Ciclo": round(media, 2),
            "Percentil 25 Lucros Até o Ciclo": round(perc25, 2)
        })

    return resumo, pd.DataFrame(resumo)
