# services/analysis/lucro.py
from __future__ import annotations

import re
from typing import Optional, Tuple

import numpy as np
import pandas as pd

# usamos o mesmo formatador de duração do módulo de endividamento
from services.analysis.endividamento import formatar_duracao

_LUCRO_RE = re.compile(r"L(\d+)", re.IGNORECASE)
_CICLO_DIV_RE = re.compile(r"D(\d+)", re.IGNORECASE)


# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

def _ensure_series_num(s: pd.Series) -> pd.Series:
    return pd.to_numeric(s, errors="coerce").fillna(0.0)

def _ensure_ciclo_int(df: pd.DataFrame) -> pd.Series:
    """
    Retorna uma série de ciclo (inteiro) com o melhor esforço:
    - prioriza 'ID Ciclo' se existir,
    - senão tenta extrair de 'ID Dívida' (D#) ou 'ID Operação' (D#),
    - por fim, se existir 'ciclo' já numérica, usa.
    """
    if "ID Ciclo" in df.columns:
        return pd.to_numeric(df["ID Ciclo"], errors="coerce").fillna(0).astype(int)

    base = None
    if "ID Dívida" in df.columns:
        base = df["ID Dívida"].astype(str).str.extract(_CICLO_DIV_RE, expand=False)
    elif "ID Operação" in df.columns:
        base = df["ID Operação"].astype(str).str.extract(_CICLO_DIV_RE, expand=False)

    if base is not None:
        return base.fillna("0").astype(int) + 1

    if "ciclo" in df.columns:
        return pd.to_numeric(df["ciclo"], errors="coerce").fillna(0).astype(int)

    # fallback neutro
    return pd.Series(0, index=df.index, dtype=int)

def _extract_lucro_id(s: str) -> Optional[int]:
    if not isinstance(s, str):
        s = str(s) if s is not None else ""
    m = _LUCRO_RE.search(s)
    return int(m.group(1)) if m else None


# ------------------------------------------------------------------------------
# 1) Resumo simples (mantém as mesmas chaves do teu front)
# ------------------------------------------------------------------------------

def resumir_ciclos_lucro_real(df_ciclos_lucro: pd.DataFrame) -> dict:
    """
    Retorna:
        - Quantidade total
        - Maior lucro
        - Média dos lucros
        - Percentil 75
        - Último lucro registrado (ciclo atual)
    Compatível com o front atual (mesmas chaves).
    """
    try:
        if df_ciclos_lucro is None or df_ciclos_lucro.empty:
            return {
                "Quantidade total": 0,
                "Maior lucro": 0.0,
                "Média dos lucros": 0.0,
                "Percentil 75": 0.0,
                "Último lucro registrado (ciclo atual)": 0.0,
            }

        df = df_ciclos_lucro.copy()

        lucro_col = (
            "Lucro Gerado no Ciclo"
            if "Lucro Gerado no Ciclo" in df.columns
            else ("Lucro Gerado" if "Lucro Gerado" in df.columns else None)
        )

        if lucro_col is None:
            return {
                "Quantidade total": int(len(df)),
                "Maior lucro": 0.0,
                "Média dos lucros": 0.0,
                "Percentil 75": 0.0,
                "Último lucro registrado (ciclo atual)": 0.0,
            }

        # ordenação estável por data se disponível
        if "Data Início" in df.columns:
            ordem = pd.to_datetime(df["Data Início"], errors="coerce")
        elif "Data Fim" in df.columns:
            ordem = pd.to_datetime(df["Data Fim"], errors="coerce")
        else:
            ordem = pd.Series(range(len(df)), index=df.index)

        df = df.assign(_ordem=ordem).sort_values("_ordem", kind="stable")
        lucros = _ensure_series_num(df[lucro_col])

        qtd = int(lucros.shape[0])
        maior = float(lucros.max()) if qtd else 0.0
        media = float(lucros.mean()) if qtd else 0.0
        p75 = float(np.percentile(lucros, 75)) if qtd >= 2 else media
        ultimo = float(lucros.iloc[-1]) if qtd else 0.0

        return {
            "Quantidade total": qtd,
            "Maior lucro": round(maior, 2),
            "Média dos lucros": round(media, 2),
            "Percentil 75": round(p75, 2),
            "Último lucro registrado (ciclo atual)": round(ultimo, 2),
        }
    except Exception:
        return {
            "Quantidade total": 0,
            "Maior lucro": 0.0,
            "Média dos lucros": 0.0,
            "Percentil 75": 0.0,
            "Último lucro registrado (ciclo atual)": 0.0,
        }


# ------------------------------------------------------------------------------
# 2) Métricas linha a linha (vetorizado, sem loops pesados)
# ------------------------------------------------------------------------------

def adicionar_metricas_lucro_linha_a_linha(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adiciona ao DF:
      - Lucro Acumulado (por ciclo, apenas somando lucros > 0)
      - Média das Máximas dos Lucros (de ciclos anteriores)
      - Percentil 25 das Máximas dos Lucros (de ciclos anteriores)
      - Posição Relativa Lucro (lucro_acum_atual / melhor_lucro_historico)
    Mantém os mesmos nomes de colunas que tu já exibias no painel.
    """
    if df is None or df.empty:
        return df

    out = df.copy()
    luc = _ensure_series_num(out.get("Lucro Gerado", 0.0))
    ciclo = _ensure_ciclo_int(out)

    out["__ciclo__"] = ciclo

    # lucro acumulado por ciclo (somando somente lucros > 0)
    luc_pos = luc.where(luc > 0, 0.0)
    out["Lucro Acumulado"] = luc_pos.groupby(out["__ciclo__"], sort=False).cumsum()

    # máximo do lucro acumulado em cada ponto do ciclo
    # (rolling cummax por grupo)
    out["__max_ciclo__"] = out.groupby("__ciclo__", sort=False)["Lucro Acumulado"].cummax()

    # melhor lucro histórico até o momento (cummax global)
    out["__max_hist__"] = out["Lucro Acumulado"].cummax()

    # posição relativa
    denom = out["__max_hist__"].replace(0, np.nan)
    out["Posição Relativa Lucro"] = (out["Lucro Acumulado"] / denom).fillna(0.0).round(2)

    # Média e P25 das máximas dos lucros de ciclos anteriores:
    # 1) pega o melhor de cada ciclo (último valor do cummax dentro do ciclo)
    best_by_cycle = out.groupby("__ciclo__", sort=False)["__max_ciclo__"].transform("max")
    # 2) transforma em série apenas onde o ciclo "vira" (fim lógico do ciclo no DF)
    fim_ciclo_mask = out["__ciclo__"].ne(out["__ciclo__"].shift(-1))  # último índice de cada ciclo
    best_list = out.loc[fim_ciclo_mask, ["__ciclo__", "__max_ciclo__"]].rename(
        columns={"__max_ciclo__": "best"}
    ).reset_index(drop=True)

    # 3) para cada linha, média/p25 das 'best' de ciclos anteriores ao seu ciclo
    # mapeia ciclo atual -> índice de posição em best_list
    ciclo_pos = out["__ciclo__"].map({c: i for i, c in enumerate(best_list["__ciclo__"])})
    medias = []
    p25s = []
    for i, cpos in ciclo_pos.items():
        if pd.isna(cpos) or cpos <= 0:
            medias.append(out.at[i, "__max_ciclo__"])
            p25s.append(out.at[i, "__max_ciclo__"])
        else:
            prev = best_list.loc[: int(cpos) - 1, "best"].values
            media = float(prev.mean()) if prev.size else float(out.at[i, "__max_ciclo__"])
            p25 = float(np.percentile(prev, 25)) if prev.size >= 2 else media
            medias.append(round(media, 2))
            p25s.append(round(p25, 2))

    out["Média das Máximas dos Lucros"] = medias
    out["Percentil 25 das Máximas dos Lucros"] = p25s

    # limpeza
    out.drop(columns=["__ciclo__", "__max_ciclo__", "__max_hist__"], inplace=True, errors="ignore")
    return out


# ------------------------------------------------------------------------------
# 3) Resumo de ciclos de lucro (L#), usando dívida==0 como fronteira
# ------------------------------------------------------------------------------

def gerar_resumo_e_dataframe_ciclos_lucro(df: pd.DataFrame) -> Tuple[list[dict], pd.DataFrame]:
    """
    Identifica sequências de 'Lucro Gerado' > 0 **com 'Dívida Acumulada' == 0** (lucro “puro”),
    acumula por bloco, e retorna (resumo:list[dict], df_resumo:DataFrame).

    Robusto a índices duplicados: usa posição (iloc) em vez de label (loc).
    """
    if df is None or df.empty:
        return [], pd.DataFrame(columns=[
            "ID Ciclo de Lucro", "Data Início", "Data Fim", "Duração do Ciclo",
            "Lucro Gerado no Ciclo", "Média Lucros Até o Ciclo", "Percentil 25 Lucros Até o Ciclo"
        ])

    out = []
    maximos_anteriores: list[float] = []

    luc = _ensure_series_num(df.get("Lucro Gerado", 0.0))
    div = _ensure_series_num(df.get("Dívida Acumulada", 0.0))
    idop = df.get("ID Operação", pd.Series([""] * len(df), index=df.index)).astype(str)

    # para converter posição -> timestamp usamos o index por posição
    idx_series = pd.Index(df.index)

    em_bloco = False
    ini_pos: Optional[int] = None
    lucro_total: float = 0.0
    id_lucro_atual: Optional[int] = None

    n = len(df)
    for pos in range(n):
        v_luc = float(luc.iloc[pos])
        v_div = float(div.iloc[pos])
        s = idop.iloc[pos]
        lid = _extract_lucro_id(s)

        if v_luc > 0 and v_div == 0:
            if not em_bloco:
                em_bloco = True
                ini_pos = pos
                lucro_total = v_luc
                id_lucro_atual = lid
            else:
                lucro_total += v_luc
        else:
            if em_bloco:
                # fecha bloco do ini_pos até pos-1
                try:
                    dt_ini = pd.to_datetime(idx_series[ini_pos])
                    dt_fim = pd.to_datetime(idx_series[pos])
                    dur = dt_fim - dt_ini
                except Exception:
                    dt_ini, dt_fim, dur = idx_series[ini_pos], idx_series[pos], pd.Timedelta(0)

                media_prev = float(np.mean(maximos_anteriores)) if maximos_anteriores else 0.0
                p25_prev = float(np.percentile(maximos_anteriores, 25)) if len(maximos_anteriores) >= 2 else media_prev

                out.append({
                    "ID Ciclo de Lucro": id_lucro_atual,
                    "Data Início": str(dt_ini),
                    "Data Fim": str(dt_fim),
                    "Duração do Ciclo": formatar_duracao(dur),
                    "Lucro Gerado no Ciclo": round(lucro_total, 2),
                    "Média Lucros Até o Ciclo": round(media_prev, 2),
                    "Percentil 25 Lucros Até o Ciclo": round(p25_prev, 2),
                })

                maximos_anteriores.append(lucro_total)
                em_bloco = False
                ini_pos = None
                lucro_total = 0.0
                id_lucro_atual = None

    # terminou dentro de um bloco -> fecha até a última linha
    if em_bloco and ini_pos is not None:
        try:
            dt_ini = pd.to_datetime(idx_series[ini_pos])
            dt_fim = pd.to_datetime(idx_series[-1])
            dur = dt_fim - dt_ini
        except Exception:
            dt_ini, dt_fim, dur = idx_series[ini_pos], idx_series[-1], pd.Timedelta(0)

        media_prev = float(np.mean(maximos_anteriores)) if maximos_anteriores else 0.0
        p25_prev = float(np.percentile(maximos_anteriores, 25)) if len(maximos_anteriores) >= 2 else media_prev

        out.append({
            "ID Ciclo de Lucro": id_lucro_atual,
            "Data Início": str(dt_ini),
            "Data Fim": str(dt_fim),
            "Duração do Ciclo": formatar_duracao(dur),
            "Lucro Gerado no Ciclo": round(lucro_total, 2),
            "Média Lucros Até o Ciclo": round(media_prev, 2),
            "Percentil 25 Lucros Até o Ciclo": round(p25_prev, 2),
        })

    return out, pd.DataFrame(out)

