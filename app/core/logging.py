# app/core/logging.py
import logging
import sys
from .config import settings

FMT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DATEFMT = "%Y-%m-%d %H:%M:%S"


def init_logging(level: int | None = None) -> None:
    """Inicializa logging raiz com um StreamHandler padrão.
    Usa INFO em dev e WARNING em produção, caso não informado.
    """
    if level is None:
        level = logging.INFO if settings.ENV != "production" else logging.WARNING

    root = logging.getLogger()
    # Evita múltiplos handlers em recargas do Flask
    for h in list(root.handlers):
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(FMT, DATEFMT))

    root.setLevel(level)
    root.addHandler(handler)