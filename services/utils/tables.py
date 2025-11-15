"""
PT:
Utilitários de DataFrame para planilhas: detecção de cabeçalho real e definição de índice datetime.

EN:
DataFrame utilities for spreadsheets: real header detection and datetime index setup.
"""

from __future__ import annotations

import logging
from typing import Iterable, Optional

import pandas as pd


def detectar_e_definir_cabecalho_real(
    df: pd.DataFrame,
    termo_cabecalho: str = "Ativo",
    *,
    strip: bool = True,
) -> Optional[pd.DataFrame]:
    """
    PT:
        Detecta automaticamente a linha do cabeçalho real com base em um termo de referência
        (padrão: "Ativo"), redefine os nomes das colunas e remove as linhas acima do cabeçalho.

    EN:
        Auto-detects the true header row using a reference term (default: "Ativo"),
        sets the DataFrame columns from that row, and drops all rows above it.
    """
    try:
        idx = df[df.eq(termo_cabecalho).any(axis=1)].index[0]
        new_cols = df.iloc[idx].astype(str).tolist()
        if strip:
            new_cols = [c.strip() for c in new_cols]
        df = df.iloc[idx + 1:].reset_index(drop=True)
        df.columns = new_cols
        logging.info("✅ Cabeçalho real detectado em linha %s e aplicado com sucesso.", idx)
        return df
    except IndexError:
        logging.error("⚠️ Cabeçalho com termo '%s' não encontrado.", termo_cabecalho)
        return None
    except Exception as e:
        logging.error("⚠️ Erro ao detectar/definir cabeçalho real: %s", e)
        return None


def definir_indice_datetime_por_candidatos(
    df: pd.DataFrame,
    candidatos_coluna_data: Iterable[str] = ("Abertura", "Data", "Data/Hora Entrada"),
    *,
    formato: Optional[str] = "%Y-%m-%d %H:%M:%S",
    dayfirst: bool = True,
    errors: str = "coerce",
) -> pd.DataFrame:
    """
    PT:
        Define o índice usando a primeira coluna candidata encontrada e converte para datetime.

    EN:
        Sets the index using the first candidate column found and converts to datetime.
    """
    try:
        chosen = None
        for col in candidatos_coluna_data:
            if col in df.columns:
                chosen = col
                break
        if chosen is None:
            logging.info("ℹ️ Nenhuma coluna de data encontrada entre os candidatos: %s", list(candidatos_coluna_data))
            return df

        df = df.set_index(chosen)
        if formato is None:
            df.index = pd.to_datetime(df.index, errors=errors, dayfirst=dayfirst)
        else:
            df.index = pd.to_datetime(df.index, errors=errors, format=formato)
        logging.info("✅ Índice datetime definido com coluna '%s'.", chosen)
        return df
    except Exception as e:
        logging.error("⚠️ Erro ao definir índice datetime: %s", e)
        return df
