"""
PT:
E/S de arquivos (JSON/CSV) e geração de modelos/placeholder para o Insight Futures.

- carregar_json: carrega JSON a partir de (diretório, nome_arquivo)
- salvar_resultados: persiste DataFrame em CSV (padrão ; e index=True para compatibilidade atual)
- gerar_modelo_json / gerar_todos_modelos_json: criam "esqueletos" de arquivos a partir de exemplos
- helpers de placeholder e timestamp

EN:
File I/O (JSON/CSV) and template/placeholder generation for Insight Futures.

- carregar_json: loads JSON from (directory, file_name)
- salvar_resultados: saves DataFrame to CSV (default ; and index=True for current compatibility)
- gerar_modelo_json / gerar_todos_modelos_json: create "skeleton" files from real examples
- placeholder and timestamp helpers
"""

from datetime import datetime
import json
import logging
import os
from typing import Any, Optional, List

import pandas as pd

from .formatters import formatar_colunas_para_br


def arquivo_permitido(nome_arquivo: str, extensoes_validas: List[str]) -> bool:
    """PT: Verifica se a extensão do arquivo é permitida. | EN: Checks if file extension is allowed."""
    return "." in nome_arquivo and nome_arquivo.rsplit(".", 1)[1].lower() in extensoes_validas


def carregar_json(diretorio: str, nome_arquivo: str, *, raise_if_missing: bool = True, default=None):
    """
    PT:
        Carrega um JSON a partir de (diretório, nome_arquivo).
        Quando raise_if_missing=False, retorna `default` se o arquivo não existir.

    EN:
        Loads a JSON from (directory, file_name).
        When raise_if_missing=False, returns `default` if the file does not exist.
    """
    import os
    import json
    import logging

    caminho = os.path.join(diretorio, nome_arquivo)
    if not os.path.exists(caminho):
        if raise_if_missing:
            raise FileNotFoundError(f"Arquivo não encontrado: {caminho}")
        logging.warning("⚠️ JSON ausente, usando default. Caminho: %s", caminho)
        return default

    with open(caminho, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar_resultados(
    df: pd.DataFrame,
    caminho: str = "analiseresultados.csv",
    formatar_monetarios: bool = False,
    colunas_monetarias: Optional[List[str]] = None,
) -> None:
    """
    PT: Salva DataFrame em CSV. Por padrão usa separador ';' e mantém index=True (compatibilidade atual do front).
    EN: Saves DataFrame to CSV. Uses ';' and keeps index=True by default (current frontend compatibility).
    """
    try:
        if df.empty:
            logging.error("⚠️ ERRO: DataFrame está vazio. Nada será salvo.")
            return

        if formatar_monetarios and colunas_monetarias:
            df = formatar_colunas_para_br(df.copy(), colunas_monetarias)

        diretorio = os.path.dirname(caminho)
        if diretorio and not os.path.exists(diretorio):
            os.makedirs(diretorio, exist_ok=True)

        df.to_csv(caminho, sep=";", index=True, encoding="utf-8-sig")
        logging.info(
            "✅ Resultados salvos em %s%s",
            caminho,
            " com valores formatados para reais." if formatar_monetarios else ".",
        )
    except Exception as e:
        logging.error("⚠️ ERRO ao salvar resultados: %s", e)





def salvar_json(data: Any, caminho: str) -> None:
    """PT/EN: Salva dados como JSON no caminho informado."""
    os.makedirs(os.path.dirname(caminho) or ".", exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def salvar_json_com_timestamp(data: Any, base_path: str, nome_base: str) -> None:
    """PT/EN: Salva JSON adicionando timestamp ao nome base."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    caminho = os.path.join(base_path, f"{nome_base}_{timestamp}.json")
    salvar_json(data, caminho)




