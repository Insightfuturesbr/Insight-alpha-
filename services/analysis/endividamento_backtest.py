from datetime import timedelta
import logging
import re
import traceback

import numpy as np
import pandas as pd


def formatar_duracao(duracao: timedelta) -> str:
    if pd.isna(duracao): # Add this check
        return "" # Or some other default value like "N/A"
    total_min = int(duracao.total_seconds() // 60)
    dias = total_min // (24 * 60)
    horas = (total_min % (24 * 60)) // 60
    minutos = total_min % 60

    partes = []
    if dias > 0:
        partes.append(f"{dias}d")
    if horas > 0:
        partes.append(f"{horas}h")
    if minutos > 0 or not partes:
        partes.append(f"{minutos}min")
    return " ".join(partes)

def gerar_resumo_e_dataframe_ciclos_divida_backtest(df: pd.DataFrame):
    resumo, maximas_anteriores = [], []
    id_divida_anterior, data_inicio, max_divida, data_ant= None, None, 0, None

    for i, row in df.iterrows():
        id_op = row["ID Operação"]
        divida = row["Dívida Acumulada"]            # negativa
        data   = row.name

        match = re.search(r'D(\d+)', id_op)
        id_div_atual = int(match.group(1)) if match else None

        if id_div_atual != id_divida_anterior:
            if id_divida_anterior is not None and max_divida < 0:
                dur = data_ant - data_inicio
                media = float(np.mean(maximas_anteriores)) if maximas_anteriores else 0.0
                perc25 = float(np.percentile(maximas_anteriores, 25)) if len(maximas_anteriores) >= 2 else media

                resumo.append({
                    "ID Ciclo": id_divida_anterior,
                    "Data Início": str(data_inicio),
                    "Data Fim":    str(data_ant),
                    "Duração do Ciclo": formatar_duracao(dur),
                    "Máxima Dívida do Ciclo": round(max_divida, 2),
                    "Média Máximas Até o Ciclo": round(media, 2),
                    # cabeçalho antigo preservado ↓
                    "Percentil 75 Máximas Até o Ciclo": round(perc25, 2)
                })
                maximas_anteriores.append(max_divida)

            max_divida, data_inicio = divida, data
        else:
            max_divida = min(max_divida, divida)     # mais negativo

        id_divida_anterior, data_ant = id_div_atual, data

    # último ciclo
    if id_divida_anterior is not None and max_divida < 0:
        dur = data_ant - data_inicio
        media = float(np.mean(maximas_anteriores)) if maximas_anteriores else 0.0
        perc25 = float(np.percentile(maximas_anteriores, 25)) if len(maximas_anteriores) >= 2 else media

        resumo.append({
            "ID Ciclo": id_divida_anterior,
            "Data Início": str(data_inicio),
            "Data Fim":    str(data_ant),
            "Duração do Ciclo": formatar_duracao(dur),
            "Máxima Dívida do Ciclo": round(max_divida, 2),
            "Média Máximas Até o Ciclo": round(media, 2),
            "Percentil 75 Máximas Até o Ciclo": round(perc25, 2)
        })

    return resumo, pd.DataFrame(resumo)