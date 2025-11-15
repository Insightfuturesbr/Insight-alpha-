from __future__ import annotations

from typing import Any, Dict

from services.unified.inputs import load_prebacktest
from services.unified.backtest import run_backtest


def run_all(params: Dict[str, Any], *, temp_path: str) -> Dict[str, Any]:
    """Minimal orchestrator: load inputs → run backtest → return payload.

    Keeps existing logic untouched; adds only glue.
    """
    df_pre = load_prebacktest(temp_path)

    metricas_backtest, metricas_original, frase = run_backtest(
        df_pre, params, temp_path=temp_path
    )

    return {
        "metricas_backtest": metricas_backtest,
        "metricas_original": metricas_original,
        "frase_dr_drawdown": frase,
    }

