"""
PT:
Validações e geração de mensagens textuais sobre período da base (para exibição no painel).
Observação: escrita aqui não exporta/“escreve” arquivos; a exportação vive em services/utils/file_io.py.

EN:
Validations and textual messages about the dataset period (for UI).
Note: actual file writing lives in services/utils/file_io.py.
"""

import logging
import pandas as pd
from services.utils.metrics import obter_periodo


def intervalo_de_datas(df: pd.DataFrame) -> str:
    """
    PT:
        Retorna uma string amigável com o período coberto (min→max) usando o índice datetime.
        Encaminha para utils.metrics.obter_periodo para manter padrão único.

    EN:
        Returns a friendly string with the covered period (min→max) from datetime index.
        Delegates to utils.metrics.obter_periodo to keep a single source of truth.
    """
    try:
        return obter_periodo(df)
    except Exception as e:
        return f"⚠️ ERRO ao obter período: {e}"


def valida_periodo_minimo(df: pd.DataFrame, min_dias: int = 10) -> None:
    """
    PT:
        Garante que o DataFrame possua pelo menos `min_dias` entre a data mínima e máxima do índice.
        Lança exceção se vazio, índice não for datetime ou período insuficiente.

    EN:
        Ensures the DataFrame covers at least `min_dias` between min and max index dates.
        Raises if empty, non-datetime index, or insufficient period.
    """
    if df.empty:
        raise ValueError("⚠️ O DataFrame está vazio e não pode ser validado.")

    if not isinstance(df.index, pd.DatetimeIndex):
        raise TypeError("⚠️ O índice do DataFrame precisa ser do tipo datetime.")

    dias = (df.index.max() - df.index.min()).days
    if dias < min_dias:
        periodo = obter_periodo(df)
        raise ValueError(f"❌ Período insuficiente ({periodo}). Mínimo exigido: {min_dias} dias.")

    logging.info("✅ Período válido (%d dias). Mínimo exigido: %d dias.", dias, min_dias)
