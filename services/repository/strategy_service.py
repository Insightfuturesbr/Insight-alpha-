# services/strategy_service.py
"""Service layer for managing strategies, uploads and insights (1:N)."""
from __future__ import annotations

import json
import os
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Ajuste o caminho dos modelos conforme seu projeto
from models.strategy import Base, Strategy, Upload, StrategyUpload, Insight


# --- DB setup ---------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.abspath(os.path.join(BASE_DIR, "..", "dataset", "strategies.db"))
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

DATABASE_URL = f"sqlite:///{DB_PATH}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

Base.metadata.create_all(engine)


@contextmanager
def get_session() -> Session:
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def _jsonify_params(data: Dict[str, Any]) -> Dict[str, Any]:
    out = dict(data)
    if isinstance(out.get("parametros"), dict):
        out["parametros"] = json.dumps(out["parametros"], ensure_ascii=False)
    return out


# --- Estratégias ------------------------------------------------------------
def create_strategy(data: Dict[str, Any]) -> Dict[str, Any]:
    payload = _jsonify_params(data)
    with get_session() as s:
        st = Strategy(**payload)
        s.add(st)
        s.flush()
        s.refresh(st)
        return st.to_dict()


def list_strategies(owner: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_session() as s:
        q = s.query(Strategy)
        if owner:
            q = q.filter(Strategy.owner == owner)
        rows = q.order_by(Strategy.created_at.desc()).all()
        return [x.to_dict() for x in rows]


def get_strategy(strategy_id: int) -> Optional[Dict[str, Any]]:
    with get_session() as s:
        st = s.get(Strategy, strategy_id)
        return st.to_dict() if st else None


def update_strategy(strategy_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    payload = _jsonify_params(data)
    allowed = {c.key for c in Strategy.__table__.columns if c.key != "id"}
    with get_session() as s:
        st = s.get(Strategy, strategy_id)
        if not st:
            return None
        for k, v in payload.items():
            if k in allowed:
                setattr(st, k, v)
        s.flush()
        s.refresh(st)
        return st.to_dict()


def delete_strategy(strategy_id: int) -> bool:
    with get_session() as s:
        st = s.get(Strategy, strategy_id)
        if not st:
            return False
        s.delete(st)
        return True


# --- Uploads (1:N) ----------------------------------------------------------
def register_upload(
    *,
    owner: str,
    filename: str,
    path: str,
    filetype: str,
    size_bytes: int,
    checksum: str,
) -> Dict[str, Any]:
    """Cria um registro de upload (vínculo com strategy é feito via attach_upload)."""
    with get_session() as s:
        up = Upload(
            owner=owner,
            filename=filename,
            path=path,
            filetype=filetype,
            size_bytes=size_bytes,
            checksum=checksum,
        )
        s.add(up)
        s.flush()
        s.refresh(up)
        return up.to_dict()


def update_upload_result_dir(upload_id: int, result_dir: str) -> Dict[str, Any]:
    """Grava o diretório de resultados dessa execução no Upload (requer coluna result_dir)."""
    with get_session() as s:
        up: Upload = s.get(Upload, int(upload_id))
        if not up:
            return {}
        setattr(up, "result_dir", result_dir)  # coluna TEXT/NULL no modelo Upload
        s.add(up)
        s.flush()
        s.refresh(up)
        return up.to_dict()


def get_upload(upload_id: int) -> Optional[Dict[str, Any]]:
    with get_session() as s:
        up = s.get(Upload, int(upload_id))
        return up.to_dict() if up else None


def list_uploads_for_strategy(strategy_id: int) -> List[Dict[str, Any]]:
    """Lista uploads (mais recentes primeiro) vinculados a uma estratégia."""
    with get_session() as s:
        rows = (
            s.query(Upload)
            .join(StrategyUpload, StrategyUpload.upload_id == Upload.id)
            .filter(StrategyUpload.strategy_id == int(strategy_id))
            .order_by(Upload.created_at.desc())
            .all()
        )
        return [r.to_dict() for r in rows]


def list_strategy_uploads(strategy_id: int) -> List[Dict[str, Any]]:
    """Compat: via relacionamento ORM direto."""
    with get_session() as s:
        st = s.get(Strategy, strategy_id)
        return [u.to_dict() for u in (st.uploads if st else [])]


def attach_upload(strategy_id: int, upload_id: int) -> bool:
    """Vincula upload à estratégia (evita duplicatas)."""
    with get_session() as s:
        st = s.get(Strategy, strategy_id)
        up = s.get(Upload, upload_id)
        if not st or not up:
            return False
        exists = (
            s.query(StrategyUpload)
            .filter_by(strategy_id=strategy_id, upload_id=upload_id)
            .first()
        )
        if not exists:
            s.add(StrategyUpload(strategy_id=strategy_id, upload_id=upload_id))
        return True


# --- Cards / Dashboard -------------------------------------------------------
def list_strategy_cards(owner: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retorna dados para os cards:
      - dados básicos da Strategy (to_dict)
      - uploads_count: total de uploads vinculados
      - last_upload: último upload (para filename, id, result_dir, etc.)
    """
    with get_session() as s:
        q = s.query(Strategy)
        if owner:
            q = q.filter(Strategy.owner == owner)
        rows = q.order_by(Strategy.created_at.desc()).all()

        cards: List[Dict[str, Any]] = []
        for st in rows:
            # total de uploads via N-N
            count = (
                s.query(StrategyUpload)
                .filter(StrategyUpload.strategy_id == st.id)
                .count()
            )

            # último upload via JOIN (mais recente)
            last_up = (
                s.query(Upload)
                .join(StrategyUpload, StrategyUpload.upload_id == Upload.id)
                .filter(StrategyUpload.strategy_id == st.id)
                .order_by(Upload.created_at.desc())
                .first()
            )

            cards.append(
                {
                    **st.to_dict(),
                    "uploads_count": count,
                    "last_upload": last_up.to_dict() if last_up else None,
                }
            )

        return cards


# --- Insights ---------------------------------------------------------------
def create_insight(
    strategy_id: int, title: str, json_path: Optional[str] = None
) -> Dict[str, Any]:
    with get_session() as s:
        st = s.get(Strategy, strategy_id)
        if not st:
            raise ValueError("Strategy not found")
        ins = Insight(strategy_id=strategy_id, title=title, json_path=json_path)
        s.add(ins)
        s.flush()
        s.refresh(ins)
        return ins.to_dict()


def list_insights(strategy_id: int) -> List[Dict[str, Any]]:
    with get_session() as s:
        rows = (
            s.query(Insight)
            .filter(Insight.strategy_id == strategy_id)
            .order_by(Insight.created_at.desc())
            .all()
        )
        return [i.to_dict() for i in rows]
