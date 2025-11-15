from __future__ import annotations

from typing import Any, Dict, Tuple

import pandas as pd

from services.logic.backtest import executar_backtest_completo, gerar_frase_insight
from services.utils.formatters import converter_valores_json_serializaveis


def run_backtest(df_prebacktest: pd.DataFrame, params: Dict[str, Any], *, temp_path: str) -> Tuple[Dict[str, Any], Dict[str, Any], str]:
    """Execute the backtest using existing logic and return metrics + insight text.

    Returns: (metricas_backtest, metricas_original, frase_dr_drawdown)
    """
    # Delegate to the existing orchestrator; it persists artifacts as side effects
    _df_recalc, metricas_backtest, metricas_original = executar_backtest_completo(
        df_prebacktest, params, temp_path=temp_path, salvar_resultados=True
    )

    # Build the phrase the same way the existing route does
    parametros_insight = {
        "ativar_percentual": params.get("ativacao_percentual", 0),
        "base_drawdown_ativar": params.get("ativacao_base", "Média dos Drawdowns"),
        "pausar_percentual": params.get("pausa_percentual", 0),
        "base_lucro_pausar": params.get("pausa_base", "Média dos Lucros"),
        "desativar_percentual": params.get("desativacao_percentual", 0),
        "base_drawdown_desativar": params.get("desativacao_base", "Maior Drawdown Histórico"),
    }
    frase = gerar_frase_insight(parametros_insight, {
        "drawdown_maximo_simulado": metricas_backtest.get("drawdown_maximo", 0),
        "meta_lucro_simulado": metricas_backtest.get("soma_lucro_gerado", 0),
    })

    # Ensure JSON‑safe numbers
    return (
        converter_valores_json_serializaveis(metricas_backtest),
        converter_valores_json_serializaveis(metricas_original),
        frase,
    )

