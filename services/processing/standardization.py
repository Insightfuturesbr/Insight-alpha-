# services/processing/standardization.py
# Padronização de P&L: valida delta vs tick, converte para ticks e calcula Bruto/Líquido + acumulados.
from __future__ import annotations
from typing import Optional, Tuple
import numpy as np, pandas as pd
from services.input.ativos import identificar_parametros_por_ativo, ParametrosAtivo

COL_PRECO_VENDA = "Preço Venda"
COL_PRECO_COMPRA = "Preço Compra"
COL_TICK_ORIGEM = "Deslocamento do ativo antes da padronização"

def validar_delta(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in (COL_PRECO_VENDA, COL_PRECO_COMPRA, COL_TICK_ORIGEM):
        if c not in out.columns: out[c] = np.nan
    venda  = pd.to_numeric(out[COL_PRECO_VENDA], errors="coerce")
    compra = pd.to_numeric(out[COL_PRECO_COMPRA], errors="coerce")
    tick_linha = pd.to_numeric(out[COL_TICK_ORIGEM], errors="coerce")
    delta = venda - compra
    out["delta_preco"] = delta
    desvio = pd.Series(np.nan, index=out.index, dtype=float)
    mask = tick_linha.notna() & (tick_linha != 0)
    desvio.loc[mask] = delta.loc[mask] - tick_linha.loc[mask]
    out["desvio_vs_tick"] = desvio
    out["alerta_tick_invalido"] = False
    out.loc[mask & (desvio.abs() > (tick_linha.abs()/2.0)), "alerta_tick_invalido"] = True
    return out

# alias de transição, caso algum ponto ainda chame o nome antigo
identificar_diferenca_com_validacao = validar_delta

def padronizar_estrategia(df: pd.DataFrame, contratos_usuario: Optional[int]=None
) -> Tuple[pd.DataFrame, Optional[ParametrosAtivo]]:
    if "Ativo" not in df.columns or df["Ativo"].dropna().empty:
        return df, None
    df = validar_delta(df)
    ativo = df["Ativo"].dropna().iloc[0]
    params = identificar_parametros_por_ativo(ativo)
    contratos = int(contratos_usuario or params.contratos)
    tick = float(getattr(params, "deslocamento_min", 0.0) or 0.0)
    mult = float(params.multiplicador)
    taxa_op = float(params.taxa) * 2.0 * contratos

    delta = pd.to_numeric(df["delta_preco"], errors="coerce").fillna(0.0)
    ticks = delta if tick <= 0 else np.rint(delta / tick)

    pl_bruto   = (ticks * mult * contratos).astype(float).round(2)
    pl_liquido = (pl_bruto - taxa_op).round(2)

    df["pl_bruto_padronizado"]   = pl_bruto
    df["pl_liquido_padronizado"] = pl_liquido
    df["pl_bruto_acumulado"]     = pl_bruto.cumsum()
    df["pl_liquido_acumulado"]   = pl_liquido.cumsum()
    n = len(df)
    df["custos_operacionais_acumulados"] = np.round(taxa_op * (np.arange(n)+1), 2)
    df["ativacao_automacao"] = True

    # --- ALIÁS / COLUNAS LEGADAS (compat com painel e assign_variables) ---
    # espelha nomes novos -> nomes antigos esperados em outras partes do app
    aliases = {
        "Resultado Simulado Padronizado Bruto": "pl_bruto_padronizado",
        "Resultado Simulado Padronizado Líquido": "pl_liquido_padronizado",
        "Resultado Simulado Padronizado Bruto Acumulado": "pl_bruto_acumulado",
        "Resultado Simulado Padronizado Líquido Acumulado": "pl_liquido_acumulado",
        "Taxas Acumuladas Padronização": "custos_operacionais_acumulados",
    }
    for antigo, novo in aliases.items():
        if novo in df.columns and antigo not in df.columns:
            df[antigo] = df[novo]

    return df, params
