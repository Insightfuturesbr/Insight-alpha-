from __future__ import annotations
"""
PT:
Utilitário de lock de processamento por pasta de resultados.
Cria um arquivo oculto ".processing.lock" dentro do diretório `temp_path` enquanto
o pipeline roda. Útil para o front saber quando já pode consumir os JSONs.

EN:
Processing lock utility per results folder.
Creates a hidden ".processing.lock" file inside `temp_path` while the pipeline
is running. Helps the frontend know when it is safe to read the JSONs.
"""
import os
from typing import Optional

LOCK_NAME = ".processing.lock"

def _lock_file(temp_path: str) -> str:
    return os.path.join(temp_path, LOCK_NAME)

def create_processing_lock(temp_path: str) -> str:
    """PT: Cria o arquivo de lock. EN: Create lock file."""
    os.makedirs(temp_path, exist_ok=True)
    lf = _lock_file(temp_path)
    # cria/atualiza o mtime
    with open(lf, "w", encoding="utf-8") as f:
        f.write("locked")
    return lf

def clear_processing_lock(temp_path: str) -> None:
    """PT: Remove o arquivo de lock. EN: Remove lock file."""
    lf = _lock_file(temp_path)
    try:
        if os.path.exists(lf):
            os.remove(lf)
    except Exception:
        # não levanta erro para não mascarar o original
        pass

def is_processing_locked(temp_path: Optional[str]) -> bool:
    """PT: Retorna True se o lock existir. EN: True if lock exists."""
    if not temp_path:
        return False
    return os.path.exists(_lock_file(temp_path))
