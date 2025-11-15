from __future__ import annotations

import os
import pandas as pd
from typing import Any, Dict, Tuple

from services.utils.file_io import carregar_json


def load_prebacktest(temp_path: str) -> pd.DataFrame:
    """Load the prebacktest DataFrame saved with orient="split".

    Prefers namespaced path temp/backtest/prebacktest.json with fallback to temp/prebacktest.json
    for backward compatibility.
    """
    caminho_ns = os.path.join(temp_path, "backtest", "prebacktest.json")
    caminho_root = os.path.join(temp_path, "prebacktest.json")
    if os.path.exists(caminho_ns):
        return pd.read_json(caminho_ns, orient="split")
    return pd.read_json(caminho_root, orient="split")


def load_core_stats(temp_path: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Load drawdown and lucro stats. Prefer drawdown namespace with fallback to root."""
    drawdown_dir = os.path.join(temp_path, "drawdown")
    variaveis_fluxo = carregar_json(drawdown_dir, "variaveis_fluxo.json", raise_if_missing=False)
    if variaveis_fluxo is None:
        variaveis_fluxo = carregar_json(temp_path, "variaveis_fluxo.json")

    estatisticas_lucro = carregar_json(drawdown_dir, "estatisticas_ciclos_lucro.json", raise_if_missing=False)
    if estatisticas_lucro is None:
        estatisticas_lucro = carregar_json(temp_path, "estatisticas_ciclos_lucro.json")

    return variaveis_fluxo, estatisticas_lucro
