from __future__ import annotations

import logging
from typing import List, Any
from collections import namedtuple
from collections.abc import Iterable

def analisar_ativos(df) -> List[str]:
    """
    PT: Retorna a lista ordenada de ativos encontrados na coluna 'Ativo'.

    """
    try:
        if 'Ativo' not in df.columns:
            logging.error("⚠️ ERRO: A coluna 'Ativo' não foi encontrada no DataFrame.")
            return []
        ativos_unicos = df['Ativo'].dropna().unique()
        ativos = sorted([str(a).strip() for a in ativos_unicos])
        if len(ativos) == 1:
            logging.info("✅ As operações aconteceram em 1 ativo (%s)", ativos[0])
        else:
            logging.info("✅ As operações aconteceram em %d ativos (%s)", len(ativos), ', '.join(ativos))
        return ativos
    except Exception as e:
        logging.error("⚠️ ERRO desconhecido ao analisar os ativos: %s", e)
        return []

# Estrutura nomeada para parâmetros (tem ._asdict())
ParametrosAtivo = namedtuple("ParametrosAtivo", [
    "multiplicador", "taxa", "deslocamento_min", "valor_por_ponto", "contratos"
])

def _coagir_para_str_ativo(ativo: Any) -> str:
    """PT/EN: Se vier lista/iterável, usa o primeiro valor não vazio; caso contrário, str(ativo)."""
    if isinstance(ativo, str):
        return ativo
    if isinstance(ativo, Iterable) and not isinstance(ativo, (bytes, bytearray)):
        for v in ativo:
            s = "" if v is None else str(v).strip()
            if s:
                return s
        return ""
    return "" if ativo is None else str(ativo)

def _limpar_nome_ativo(ativo: str) -> str:
    """PT/EN: Remove prefixos e normaliza o ticker para UPPER (ex.: '[R] WINM25' → 'WINM25')."""
    return ativo.replace("[R] ", "").strip().upper()

def identificar_parametros_por_ativo(ativo: Any) -> ParametrosAtivo:
    """
    PT: Retorna parâmetros padrão para um único ativo (heurística simples).
        Aceita string ou coleção; usa o primeiro valor não vazio.
    EN: Returns default parameters for a single asset (simple heuristic).
        Accepts str or collection; uses the first non-empty value.
    """
    ativo_limpo = _limpar_nome_ativo(_coagir_para_str_ativo(ativo))

    if not ativo_limpo:
        logging.warning("⚠️ Ativo vazio/não informado. Usando parâmetros padrão.")
        return ParametrosAtivo(1.00, 0.30, 5.0, 0.20, 5)

    if ativo_limpo.startswith("WIN"):      # Mini índice
        parametros = ParametrosAtivo(1.00, 0.30, 5.0, 0.20, 5)
    elif ativo_limpo.startswith("WDO"):    # Mini dólar
        parametros = ParametrosAtivo(5.00, 1.30, 0.50, 10.00, 1)
    else:
        logging.warning("⚠️ Ativo não reconhecido: %s. Usando parâmetros padrão.", ativo_limpo)
        parametros = ParametrosAtivo(1.00, 0.30, 5.0, 0.20, 5)

    logging.info(
        "📦 Parâmetros para '%s' → multiplicador=%s, taxa=%s, deslocamento_min=%s, R$/ponto=%s, contratos=%s",
        ativo_limpo, parametros.multiplicador, parametros.taxa, parametros.deslocamento_min,
        parametros.valor_por_ponto, parametros.contratos
    )
    return parametros
