# preprocessing.py

import logging
import pandas as pd
from typing import Iterable, Optional, Set, Dict, Any

# Nomes canônicos que o pipeline usa desde o início
COL_DT_ABERTURA   = "Abertura"
COL_DT_FECHAMENTO = "Fechamento"
COL_ATIVO         = "Ativo"
COL_QTD           = "Qtd Compra"
COL_RES_REAL      = "Res. Operação"
COL_RES_PCT       = "Res. Operação (%)"
COL_PRECO_C       = "Preço Compra"
COL_PRECO_V       = "Preço Venda"

# --- Parser BR numérico (robusto, sem escalar %) ---
def _to_num(s: pd.Series) -> pd.Series:
    """
    Converte strings BR em número:
      - remove '%', não escala (mantém semântica atual)
      - se houver vírgula decimal, remove pontos de milhar antes
      - troca ',' -> '.'
      - coerces inválidos para 0.0
    """
    st = s.astype(str).str.strip()
    st = st.str.replace("%", "", regex=False)
    has_comma = st.str.contains(",", regex=False)
    st = st.mask(has_comma, st.str.replace(".", "", regex=False))
    st = st.str.replace(",", ".", regex=False)
    return pd.to_numeric(st, errors="coerce").fillna(0.0)

# --- Definir índice temporal (sem excluir Fechamento, sem remover duplicadas) ---
def definir_indice_e_datas(
    df: pd.DataFrame,
    prefer: str = COL_DT_ABERTURA,
    fallback: Optional[str] = COL_DT_FECHAMENTO,
    dayfirst: bool = True,
    ordenar: bool = True
) -> pd.DataFrame:
    """
    Garante índice temporal:
      1) Usa 'Abertura' por padrão; se ausente, tenta 'Fechamento' (se passado).
      2) Converte para datetime (dayfirst configurável).
      3) NÃO remove duplicadas (várias operações no mesmo instante são mantidas).
      4) Opcionalmente ordena pelo índice.
    """
    out = df.copy()

    col_dt = None
    if prefer in out.columns:
        col_dt = prefer
    elif fallback and fallback in out.columns:
        col_dt = fallback

    if col_dt is None:
        logging.warning("⛔ Nenhuma coluna temporal encontrada (Abertura/Fechamento). Mantendo índice atual.")
        return out

    out[col_dt] = pd.to_datetime(out[col_dt], errors="coerce", dayfirst=dayfirst)

    # set_index mantém NaT; não removemos linhas sem data por sua solicitação
    out = out.set_index(col_dt)
    if ordenar:
        out = out.sort_index()

    return out

# --- Limpador de colunas (whitelist) ---
_BASE_WHITELIST: Set[str] = {
    COL_DT_ABERTURA, COL_DT_FECHAMENTO, COL_ATIVO,
    COL_QTD, COL_RES_REAL, COL_RES_PCT,
    COL_PRECO_C, COL_PRECO_V,
    # nomes canônicos/espelhos que usamos logo no início
    "contratos_negociados", "Contratos Negociados",
    "resultado_operacao_real_antes", "Resultado da Operação em real antes da padronização",
    "deslocamento_antes", "Deslocamento do ativo antes da padronização",
}

def limpar_colunas_desnecessarias(
    df: pd.DataFrame,
    keep_extra: Optional[Iterable[str]] = None,
    preserve_prefixes: Optional[Iterable[str]] = None
) -> pd.DataFrame:
    """
    Remove colunas que não são usadas no início do pipeline.
    - keep_extra: lista de colunas extras que você quer manter.
    - preserve_prefixes: mantém qualquer coluna que comece com um desses prefixos (ex.: 'ID ', 'Taxa ').
    """
    wl = set(_BASE_WHITELIST)
    if keep_extra:
        wl.update([c for c in keep_extra if isinstance(c, str)])

    prefixes = tuple(preserve_prefixes) if preserve_prefixes else tuple()
    cols_keep = []
    for c in df.columns:
        if c in wl or (prefixes and any(str(c).startswith(p) for p in prefixes)):
            cols_keep.append(c)

    if not cols_keep:
        logging.warning("⚠️ Whitelist vazia após filtros — não removendo nada.")
        return df

    drop_cols = [c for c in df.columns if c not in cols_keep]
    if drop_cols:
        logging.info("🧹 Limpando %d colunas desnecessárias.", len(drop_cols))
        return df[cols_keep].copy()

    return df

from typing import Tuple, Optional
import pandas as pd
import numpy as np
# importa os parâmetros do ativo (como no teu arquivo original)
from services.input.ativos import identificar_parametros_por_ativo, ParametrosAtivo

# nomes de origem que vêm do Profit/planilha
COL_ATIVO     = "Ativo"
COL_QTD       = "Qtd Compra"
COL_RES_REAL  = "Res. Operação"
COL_RES_PCT   = "Res. Operação (%)"

def _to_num(s: pd.Series) -> pd.Series:
    # conversor simples BR: só troca vírgula por ponto e coerce
    return pd.to_numeric(s.astype(str).str.replace(',', '.'), errors='coerce').fillna(0.0)

def criar_colunas_operacoes(df: pd.DataFrame) -> Tuple[pd.DataFrame, Optional[ParametrosAtivo]]:
    """
    Cria as colunas canônicas 'antes da padronização' e retorna (df, params).
    - contratos_negociados
    - resultado_operacao_real_antes
    - deslocamento_antes
    - taxas_antes
    - resultado_liquido_antes (+ acumulado)
    - resultado_pontos_acumulado
    E cria espelhos legados para compat com o front/assign.
    """
    out = df.copy()

    # canônicos a partir das colunas de origem
    if COL_QTD in out.columns:
        out["contratos_negociados"] = _to_num(out[COL_QTD])
        out["Contratos Negociados"] = out["contratos_negociados"]

    if COL_RES_REAL in out.columns:
        out["resultado_operacao_real_antes"] = _to_num(out[COL_RES_REAL])
        out["Resultado da Operação em real antes da padronização"] = out["resultado_operacao_real_antes"]

    if COL_RES_PCT in out.columns:
        out["deslocamento_antes"] = _to_num(out[COL_RES_PCT])
        out["Deslocamento do ativo antes da padronização"] = out["deslocamento_antes"]

    # requeridos para seguir com cálculo de taxas/rl
    req = {"contratos_negociados", "resultado_operacao_real_antes", "deslocamento_antes", COL_ATIVO}
    if not req.issubset(out.columns):
        # se faltar algo, retorna sem params (pipeline a jusante deve lidar)
        return out, None

    # identificar parâmetros do ativo
    ativos_series = out[COL_ATIVO].dropna()
    if ativos_series.size:
        ativo_ref = str(ativos_series.iloc[0])
        params = identificar_parametros_por_ativo(ativo_ref)
    else:
        # default (como estava no código)
        params = ParametrosAtivo(1.0, 0.30, 1, 1.0, 1.0)

    # taxas por operação (duas pontas * taxa * contratos)
    taxas = (out["contratos_negociados"] * 2 * float(params.taxa)).round(2)
    rl    = (out["resultado_operacao_real_antes"] - taxas).round(2)

    out["taxas_antes"] = taxas
    out["resultado_liquido_antes"] = rl
    out["resultado_liquido_acumulado_antes"] = rl.cumsum().round(2)
    out["resultado_pontos_acumulado"] = out["deslocamento_antes"].cumsum().round(2)

    # espelhos legados (nomes esperados pelo assign/painel)
    out["Taxas antes da padronização"] = out["taxas_antes"]
    out["Resultado líquido antes da padronização"] = out["resultado_liquido_antes"]
    out["Resultado líquido Total Acumulado antes da padronização"] = out["resultado_liquido_acumulado_antes"]
    out["Resultado Total Acumulado em pontos"] = out["resultado_pontos_acumulado"]

    return out, params

