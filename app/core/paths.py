from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.core.config import settings

# strings para compat com Flask/session/JSON
UPLOAD_FOLDER = settings.uploads_dir
OUTPUTS_DIR = settings.outputs_dir

# Paths para operações locais
USUARIOS_DIR = Path(OUTPUTS_DIR) / "usuarios"
RESULTADOS_DIR = Path(OUTPUTS_DIR) / "resultados"
STATIC_DIR = Path(settings.static_dir)
TEMPLATES_DIR = Path(settings.templates_dir)

USUARIOS_DIR.mkdir(parents=True, exist_ok=True)
RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
Path(UPLOAD_FOLDER).mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"csv", "xlsx"}


def criar_diretorio_resultado(usuario: str = "admin"):
    """
    Cria diretório versionado em outputs/resultados/<usuario>_<timestamp>
    Retorna (Path, nome_sessao)
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nome = f"{usuario}_{timestamp}"
    path = RESULTADOS_DIR / nome
    path.mkdir(parents=True, exist_ok=True)
    return path, nome
