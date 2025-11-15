# services/analysis/endividamento.py
from __future__ import annotations

import re
import logging
from datetime import timedelta
from typing import Optional

import numpy as np
import pandas as pd

# -----------------------------------------------------------------------------
# Utilidades básicas
# -----------------------------------------------------------------------------

_CICLO_RE = re.compile(r"D(\d+)", re.IGNORECASE)
log = logging.getLogger(__name__)

def _ensure_id_ciclo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Garante 'ID Ciclo' a partir de 'ID Dívida' (D#) ou 'ID Operação'.
    Mantém compat com o front que às vezes espera essa coluna.
    """
    out = df
    if "ID Ciclo" in out.columns:
        out["ID Ciclo"] = pd.to_numeric(out["ID Ciclo"], errors="coerce").fillna(0).astype(int)
        return out

    base = out["ID Dívida"] if "ID Dívida" in out.columns else out.get("ID Operação", pd.Series("", index=out.index))
    ciclo = (
        base.astype(str)
        .str.extract(_CICLO_RE, expand=False)
        .fillna("0")
        .astype(int)
    )
    out["ID Ciclo"] = ciclo + 1  # convenção D0->1
    return out

def _delta_acum(s: pd.Series) -> pd.Series:
    s = pd.to_numeric(s, errors="coerce").fillna(0.0)
    return s - s.shift(fill_value=0.0)

# -----------------------------------------------------------------------------
# (1) Funções ORIGINAIS — preservadas e vetorizadas
# -----------------------------------------------------------------------------

def adicionar_fluxo_por_ciclo_linha_a_linha(df: pd.DataFrame) -> pd.DataFrame:
    """
    Versão vetorizada (sem loops) que mantém as MESMAS colunas:
      - emprestimo_acumulado_ciclo / amortizacao_acumulada_ciclo / lucro_acumulado_ciclo
      - qtd_emprestimos_ciclo / qtd_amortizacoes_ciclo / qtd_lucros_ciclo
    """
    try:
        out = df.copy()

        def _extrai_ciclo_id(serie: pd.Series) -> pd.Series:
            s = serie.astype(str).str.extract(r"(D\d+)", expand=False)
            return s.fillna("D0")

        if "ID Dívida" in out.columns:
            ciclo = _extrai_ciclo_id(out["ID Dívida"])
            if "ID Operação" in out.columns:
                faltantes = ciclo.isna() | (ciclo == "D0")
                if faltantes.any():
                    ciclo.loc[faltantes] = _extrai_ciclo_id(out.loc[faltantes, "ID Operação"])
        else:
            ciclo = _extrai_ciclo_id(out.get("ID Operação", pd.Series(index=out.index, dtype=str)))

        out["__ciclo__"] = ciclo

        # acumulados por ciclo
        for col_src, col_dst in [
            ("Valor Emprestado", "emprestimo_acumulado_ciclo"),
            ("Amortização", "amortizacao_acumulada_ciclo"),
            ("Lucro Gerado", "lucro_acumulado_ciclo"),
        ]:
            if col_src not in out.columns:
                out[col_src] = 0.0
            grp = out.groupby("__ciclo__", sort=False)[col_src]
            out[col_dst] = grp.cumsum().fillna(0.0)

        # contagens por ciclo
        for col_src, col_dst in [
            ("Valor Emprestado", "qtd_emprestimos_ciclo"),
            ("Amortização", "qtd_amortizacoes_ciclo"),
            ("Lucro Gerado", "qtd_lucros_ciclo"),
        ]:
            if col_src not in out.columns:
                out[col_src] = 0.0
            grp = out.groupby("__ciclo__", sort=False)[col_src].apply(lambda s: (s != 0).cumsum())
            out[col_dst] = grp.values

        out.drop(columns=["__ciclo__"], inplace=True)
        return out

    except Exception:
        log.exception("Falha em adicionar_fluxo_por_ciclo_linha_a_linha; retornando df original.")
        return df


def extrair_fluxo_final_por_ciclo(df: pd.DataFrame) -> dict:
    """Retorna os valores da ÚLTIMA linha (como no original)."""
    try:
        ultima = df.iloc[-1]
        colunas = [
            "emprestimo_acumulado_ciclo",
            "amortizacao_acumulada_ciclo",
            "lucro_acumulado_ciclo",
            "qtd_emprestimos_ciclo",
            "qtd_amortizacoes_ciclo",
            "qtd_lucros_ciclo",
        ]
        out = {}
        for c in colunas:
            if c in df.columns:
                val = ultima[c]
                out[c] = round(float(val), 2) if "acumulado" in c else int(val)
            else:
                log.warning("⚠️ Coluna não encontrada ao extrair fluxo final: %s", c)
                out[c] = None
        return out
    except Exception:
        log.exception("Falha em extrair_fluxo_final_por_ciclo; retornando {}.")
        return {}


def formatar_duracao(duracao: timedelta) -> str:
    if pd.isna(duracao):
        return ""
    total_min = int(duracao.total_seconds() // 60)
    d, rem = divmod(total_min, 1440)
    h, m = divmod(rem, 60)
    parts = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    if m or not parts:
        parts.append(f"{m}min")
    return " ".join(parts)


def gerar_resumo_e_dataframe_ciclos_divida(df: pd.DataFrame):
    """
    Reimplementação resiliente da tua versão original.
    Mantém chaves e rótulos (inclui 'Percentil 75 Máximas Até o Ciclo' por compat).
    """
    resumo, maximas_anteriores = [], []
    id_divida_anterior, data_inicio, max_divida, data_ant = None, None, 0.0, None

    for i, row in df.iterrows():
        id_op = str(row.get("ID Operação", ""))
        divida = float(pd.to_numeric(row.get("Dívida Acumulada", 0.0), errors="coerce"))
        data = row.name

        m = re.search(r"D(\d+)", id_op)
        id_div_atual = int(m.group(1)) if m else None

        if id_div_atual != id_divida_anterior:
            # fecha ciclo anterior
            if id_divida_anterior is not None and max_divida < 0:
                dur = data_ant - data_inicio
                media = float(np.mean(maximas_anteriores)) if maximas_anteriores else 0.0
                perc25 = float(np.percentile(maximas_anteriores, 25)) if len(maximas_anteriores) >= 2 else media

                resumo.append({
                    "ID Ciclo": id_divida_anterior,
                    "Data Início": str(data_inicio),
                    "Data Fim": str(data_ant),
                    "Duração do Ciclo": formatar_duracao(dur),
                    "Máxima Dívida do Ciclo": round(max_divida, 2),
                    "Média Máximas Até o Ciclo": round(media, 2),
                    "Percentil 75 Máximas Até o Ciclo": round(perc25, 2),  # mantém cabeçalho antigo
                })
                maximas_anteriores.append(max_divida)

            # inicia novo
            max_divida, data_inicio = divida, data
        else:
            max_divida = min(max_divida, divida)  # mais negativo

        id_divida_anterior, data_ant = id_div_atual, data

    # último ciclo
    if id_divida_anterior is not None and max_divida < 0:
        dur = data_ant - data_inicio
        media = float(np.mean(maximas_anteriores)) if maximas_anteriores else 0.0
        perc25 = float(np.percentile(maximas_anteriores, 25)) if len(maximas_anteriores) >= 2 else media

        resumo.append({
            "ID Ciclo": id_divida_anterior,
            "Data Início": str(data_inicio),
            "Data Fim": str(data_ant),
            "Duração do Ciclo": formatar_duracao(dur),
            "Máxima Dívida do Ciclo": round(max_divida, 2),
            "Média Máximas Até o Ciclo": round(media, 2),
            "Percentil 75 Máximas Até o Ciclo": round(perc25, 2),
        })

    return resumo, pd.DataFrame(resumo)


def converter_duracao_para_minutos(duracao_str: str) -> int:
    """Converte '6d 20h 34min' → minutos inteiros (compat com original)."""
    if not isinstance(duracao_str, str):
        return 0
    ds, hs, ms = 0, 0, 0
    if "d" in duracao_str:
        a, b = duracao_str.split("d", 1)
        ds = int(a.strip() or 0)
        duracao_str = b.strip()
    if "h" in duracao_str:
        a, b = duracao_str.split("h", 1)
        hs = int(a.strip() or 0)
        duracao_str = b.strip()
    if "min" in duracao_str:
        ms = int(duracao_str.replace("min", "").strip() or 0)
    return ds * 1440 + hs * 60 + ms


def obter_estatisticas_duracao_ciclos(resumo_ciclos: list[dict]) -> dict:
    """
    Mantém o shape do original: média/percentil e formato em string.
    """
    duracoes_minutos = [
        converter_duracao_para_minutos(c.get("Duração do Ciclo", ""))
        for c in resumo_ciclos
        if c.get("Duração do Ciclo")
    ]
    if not duracoes_minutos:
        return {"maxima_formatada": "", "media_formatada": "", "percentil_75_formatada": ""}

    media_min = float(np.mean(duracoes_minutos))
    maxima_min = float(np.max(duracoes_minutos))
    perc75_min = float(np.percentile(duracoes_minutos, 75))

    return {
        "maxima_formatada": formatar_duracao(timedelta(minutes=round(maxima_min))),
        "media_formatada": formatar_duracao(timedelta(minutes=round(media_min))),
        "percentil_75_formatada": formatar_duracao(timedelta(minutes=round(perc75_min))),
    }

# -----------------------------------------------------------------------------
# (2) KPIs PROPRIETÁRIOS — IED, IMD, CRD, IEA, IPR, CR, CRO, ICL
# -----------------------------------------------------------------------------

def preparar_bases_por_ciclo(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara colunas-chave e um inteiro de ciclo (0-based) para agrupamentos.
    (Mantém nomes do original para compatibilidade.)
    """
    base = _ensure_id_ciclo(df.copy())
    # ciclo inteiro (0-based internamente)
    base["ciclo"] = base["ID Ciclo"].astype(int) - 1

    base["div"] = pd.to_numeric(base.get("Dívida Acumulada", 0.0), errors="coerce").fillna(0.0)
    base["emp"] = pd.to_numeric(base.get("Valor Emprestado", 0.0), errors="coerce").fillna(0.0)
    base["amo"] = pd.to_numeric(base.get("Amortização", 0.0), errors="coerce").fillna(0.0)
    base["luc"] = pd.to_numeric(base.get("Lucro Gerado", 0.0), errors="coerce").fillna(0.0)

    if "custos_operacionais_acumulados" in base.columns:
        base["custo_linha"] = _delta_acum(base["custos_operacionais_acumulados"])
    else:
        base["custo_linha"] = 0.0

    return base


def calcular_metricas_endividamento(
    df: pd.DataFrame,
    contagens: Optional[pd.DataFrame] = None,
    custo_tempo_por_barra: float = 0.0,
) -> pd.DataFrame:
    """
    Retorna um DataFrame por ciclo com: IED, IMD, CRD, IEA, IPR, CR, CRO, ICL
    (mantendo rótulos do original + 'Maxima_Divida_do_Ciclo').
    """
    if df is None or df.empty:
        return pd.DataFrame(columns=[
            "ID Ciclo",
            "IED_Eficiencia_Declinio", "IMD_Mitigacao_Declinio", "CRD_Custo_Rel_Declinio",
            "IEA_Eficiencia_Amortizacao", "IPR_Pureza_Recuperacao",
            "CR_Custo_Recuperacao", "CRO_Custo_Real_Operacao", "ICL_Indice_Conversao_Lucro",
            "Maxima_Divida_do_Ciclo",
        ])

    b = preparar_bases_por_ciclo(df)

    # Fase por variação da dívida: declínio quando piora (fica mais negativa)
    b["delta_div"] = b.groupby("ciclo")["div"].diff().fillna(0.0)
    b["is_decl"] = b["delta_div"] < 0
    b["is_rec"] = ~b["is_decl"]

    g = b.groupby("ciclo", sort=False)

    max_div = g["div"].min()  # mais negativo
    soma_emp_d = g.apply(lambda x: (x.loc[x.is_decl, "emp"].abs()).sum())
    soma_custo_d = g.apply(lambda x: x.loc[x.is_decl, "custo_linha"].sum())
    soma_amo_d = g.apply(lambda x: x.loc[x.is_decl, "amo"].sum())

    soma_amo_r = g.apply(lambda x: x.loc[x.is_rec, "amo"].sum())
    soma_luc_r = g.apply(lambda x: x.loc[x.is_rec, "luc"].sum())
    soma_custo_r = g.apply(lambda x: x.loc[x.is_rec, "custo_linha"].sum())

    ops_d = g.apply(lambda x: int(x["is_decl"].sum()))
    ops_r = g.apply(lambda x: int(x["is_rec"].sum()))
    luc_r_ct = g.apply(lambda x: int((x["is_rec"] & (x["luc"] > 0)).sum()))

    dur_d = ops_d.replace(0, np.nan)
    dur_r = ops_r.replace(0, np.nan)

    abs_max = max_div.abs().replace(0, np.nan)

    IED = (abs_max / dur_d).replace([np.inf, -np.inf], np.nan)
    IMD = (soma_amo_d / abs_max).replace([np.inf, -np.inf], np.nan)
    CRD = (soma_custo_d / abs_max).replace([np.inf, -np.inf], np.nan)

    IEA = (soma_amo_r / dur_r).replace([np.inf, -np.inf], np.nan)
    IPR = (luc_r_ct / ops_r).replace([np.inf, -np.inf], np.nan)

    CR = soma_custo_r + (dur_r.fillna(0) * float(custo_tempo_por_barra))
    CRO = abs_max.fillna(0) + soma_custo_d.fillna(0) + soma_custo_r.fillna(0)
    ICL = (soma_luc_r / CRO.replace(0, np.nan)).replace([np.inf, -np.inf], np.nan)

    out = pd.DataFrame({
        "ID Ciclo": (IED.index.astype(int) + 1).values,
        "IED_Eficiencia_Declinio": IED.round(4).values,
        "IMD_Mitigacao_Declinio": IMD.round(4).values,
        "CRD_Custo_Rel_Declinio": CRD.round(4).values,
        "IEA_Eficiencia_Amortizacao": IEA.round(4).values,
        "IPR_Pureza_Recuperacao": IPR.round(4).values,
        "CR_Custo_Recuperacao": CR.round(2).values,
        "CRO_Custo_Real_Operacao": CRO.round(2).values,
        "ICL_Indice_Conversao_Lucro": ICL.round(4).values,
        "Maxima_Divida_do_Ciclo": max_div.round(2).values,
    }).sort_values("ID Ciclo", kind="stable").reset_index(drop=True)

    if contagens is not None and not contagens.empty:
        if "ID Ciclo" not in contagens.columns and "ciclo_id" in contagens.columns:
            c2 = contagens.copy()
            c2["ID Ciclo"] = pd.to_numeric(c2["ciclo_id"], errors="coerce").fillna(0).astype(int) + 1
            contagens = c2
        out = out.merge(contagens, on="ID Ciclo", how="left")

    return out
