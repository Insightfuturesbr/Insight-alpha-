"""
PT:
Formatação e normalização de dados:
- BR/EN monetário → float
- Correções numéricas (NaN, floor)
- Formatação BR para exibição
- Remoção/ordenação de colunas
- Conversões para JSON

EN:
Data formatting & normalization:
- BR/EN monetary → float
- Numeric fixes (NaN, floor)
- BR display formatting
- Column removal/reordering
- JSON conversions
"""

from datetime import date, datetime
import logging
import re
from typing import List, Dict, Any, Optional


import numpy as np
import pandas as pd


# -----------------------
# Formatação / Exibição
# -----------------------

def formatar_colunas_para_br(df: pd.DataFrame, colunas: List[str]) -> pd.DataFrame:
    """
    PT: Formata colunas numéricas para string no padrão brasileiro.
    EN: Formats numeric columns to Brazilian-locale strings.
    """
    def formatar(valor):
        try:
            return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return valor

    for col in colunas:
        if col in df.columns:
            df[col] = df[col].apply(formatar)
    return df


def excluir_colunas(df: pd.DataFrame, colunas_para_excluir: List[str]) -> pd.DataFrame:
    """
    PT: Remove colunas especificadas, se existirem.
    EN: Drops specified columns if present.
    """
    try:
        colunas_existentes = [c for c in colunas_para_excluir if c in df.columns]
        if colunas_existentes:
            df = df.drop(columns=colunas_existentes)
            logging.info("✅ Colunas removidas: %s", ", ".join(colunas_existentes))
        else:
            logging.info("ℹ️ Nenhuma das colunas especificadas foi encontrada.")
        return df
    except Exception as e:
        logging.error("⚠️ ERRO ao excluir colunas: %s", e)
        return df


def ordenar_colunas(df: pd.DataFrame) -> pd.DataFrame:
    """
    PT: Reorganiza o DataFrame seguindo ordem preferencial (mantém extras ao final).
    EN: Reorders DataFrame following a preferred order (keeps extras at the end).
    """
    ordem_das_colunas = [
        'ID Operação', 'Caixa Líquido',
        'Dívida Acumulada', 'Máxima Dívida Acumulada', 'Média das Máximas Dívidas', 'Posição Relativa Dívida',
        'Ciclos de Endividamento (D)', 'Ciclos de Endividamento (W)', 'Ciclos de Endividamento (M)',
        'Valor Emprestado', 'Total Empréstimos (D)', 'Total Empréstimos (W)', 'Total Empréstimos (M)',
        'Quantidade Empréstimos (D)', 'Quantidade Empréstimos (W)', 'Quantidade Empréstimos (M)',
        'Amortização',  'Total Amortizações (D)',  'Total Amortizações (W)', 'Total Amortizações (M)',
        'Quantidade Amortizações (D)', 'Quantidade Amortizações (W)', 'Quantidade Amortizações (M)',
        'Lucro Gerado', 'Total Lucro (D)','Total Lucro (W)', 'Total Lucro (M)',
        'Quantidade Lucro (D)', 'Quantidade Lucro (M)', 'Quantidade Lucro (W)',
        'Sequencia_Valores_Emprestados', 'PR_Media_SVE', 'PR_Mediana_SVE', 'PR_DesvioPadrao_SVE',
        'PR_Percentil25_SVE', 'PR_Percentil75_SVE', 'PR_Minimo_SVE', 'PR_Maximo_SVE',
        'Sequencia_Valores_Recebidos',  'PR_Media_SVR', 'PR_Mediana_SVR',  'PR_DesvioPadrao_SVR',
        'PR_Percentil25_SVR', 'PR_Percentil75_SVR', 'PR_Minimo_SVR', 'PR_Maximo_SVR'
    ]
    extras = [c for c in df.columns if c not in ordem_das_colunas]
    df = df[ordem_das_colunas + extras]
    logging.info("✅ Colunas ordenadas com sucesso!")
    return df


def extrair_id_divida(id_operacao: str) -> Optional[int]:
    """
    PT: Extrai o ID da dívida a partir do padrão do ID de operação (ex.: 'D12E3A0...').
    EN: Extracts the debt ID from the operation ID pattern (e.g., 'D12E3A0...').
    """
    try:
        match = re.search(r"D(\d+)E", id_operacao)
        return int(match.group(1)) if match else None
    except Exception as e:
        logging.error("⚠️ ERRO ao extrair ID Dívida de '%s': %s", id_operacao, e)
        return None


# -----------------------
# JSON helpers
# -----------------------

def converter_valores_json_serializaveis(dicionario: Dict[str, Any]) -> Dict[str, Any]:
    """PT/EN: Converte tipos NumPy/Datetime em equivalentes JSON-serializáveis (dict)."""
    def conv(v):
        if isinstance(v, (np.integer, np.int64, np.int32)):
            return int(v)
        if isinstance(v, (np.floating, np.float64, np.float32)):
            return float(v)
        if isinstance(v, dict):
            return {k: conv(vv) for k, vv in v.items()}
        if isinstance(v, list):
            return [conv(x) for x in v]
        return v
    return {k: conv(v) for k, v in dicionario.items()}


def converter_lista_json_serializavel(lista: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """PT/EN: Converte lista de dicts para formatos JSON-serializáveis (NumPy/Datetime → nativos)."""
    def conv(v):
        if isinstance(v, (np.integer, np.int64, np.int32)):
            return int(v)
        if isinstance(v, (np.floating, np.float64, np.float32)):
            return float(v)
        if isinstance(v, (pd.Timestamp, pd.Timedelta, datetime, date)):
            return str(v)
        if isinstance(v, (np.ndarray, list, tuple)):
            return [conv(x) for x in v]
        if isinstance(v, dict):
            return {k: conv(vv) for k, vv in v.items()}
        return v
    return [conv(item) for item in lista]


# -----------------------
# Normalização monetária / numérica
# -----------------------

def tratar_formatos_monetarios(df: pd.DataFrame, colunas_monetarias: List[str]) -> pd.DataFrame:
    """
    PT: Converte colunas monetárias BR/EN para float (ponto decimal).
    EN: Converts BR/EN monetary columns to float (dot decimal).
    """
    corrigidas = []
    for col in colunas_monetarias or []:
        if col in df.columns:
            exemplo = str(df[col].dropna().astype(str).iloc[0]) if df[col].dropna().shape[0] else ""
            if "," in exemplo and "." in exemplo:
                df[col] = (
                    df[col].astype(str).str.strip()
                    .str.replace(".", "x", regex=False)
                    .str.replace(",", ".", regex=False)
                    .str.replace("x", "", regex=False)
                )
            elif "," in exemplo:
                df[col] = df[col].astype(str).str.replace(",", ".", regex=False)
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
            corrigidas.append(col)
    if corrigidas:
        logging.info("✅ Colunas monetárias corrigidas: %s", ", ".join(corrigidas))
    return df


def corrigir_valores_numericos(df: pd.DataFrame) -> pd.DataFrame:
    """
    PT: Preenche NaN com 0 e aplica floor em colunas numéricas.
    EN: Fills NaN with 0 and applies floor to numeric columns.
    """
    cols = df.select_dtypes(include=[np.number]).columns.tolist()
    total_na = 0
    total_floor = 0.0
    for col in cols:
        na = int(df[col].isna().sum())
        total_na += na
        df[col] = df[col].fillna(0.0)
        before = float(df[col].sum())
        df[col] = np.floor(df[col]).astype(float)
        after = float(df[col].sum())
        total_floor += before - after
    logging.info("✅ NaN preenchidos: %s | Redução por floor: %s", total_na, total_floor)
    return df


def normalizar_colunas_monetarias(df: pd.DataFrame, colunas_monetarias: Optional[List[str]] = None) -> pd.DataFrame:
    """
    PT: Pipeline de normalização monetária/numérica para análises.
    EN: Monetary/numeric normalization pipeline for analytics.
    """
    try:
        if colunas_monetarias:
            df = tratar_formatos_monetarios(df, colunas_monetarias)

        for col in ["Res. Operação", "Res. Operação (%)"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype(float)

        df = corrigir_valores_numericos(df)
        return df
    except Exception as e:
        logging.error("⚠️ ERRO em normalizar_colunas_monetarias: %s", e)
        return df
