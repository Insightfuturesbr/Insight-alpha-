# models/strategy.py
from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    String, Text, DateTime, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import (
    declarative_base, relationship, Mapped, mapped_column
)

Base = declarative_base()

# ------------ Strategy ------------
class Strategy(Base):
    __tablename__ = "strategies"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(120), nullable=False)
    ativo: Mapped[Optional[str]] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30), default="draft", nullable=False)
    parametros: Mapped[Optional[str]] = mapped_column(Text)  # JSON serializado (string)
    owner: Mapped[str] = mapped_column(String(80), default="anonimo", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # N-N com Upload via strategy_uploads
    uploads: Mapped[List["Upload"]] = relationship(
        "Upload",
        secondary="strategy_uploads",
        back_populates="strategies",
        lazy="selectin",
    )

    insights: Mapped[List["Insight"]] = relationship(
        "Insight",
        back_populates="strategy",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="selectin",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nome": self.nome,
            "ativo": self.ativo,
            "status": self.status,
            "parametros": self.parametros,
            "owner": self.owner,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ------------ Upload ------------
class Upload(Base):
    __tablename__ = "uploads"

    id: Mapped[int] = mapped_column(primary_key=True)
    owner: Mapped[str] = mapped_column(String(80), default="anonimo", nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(1024), nullable=False)
    filetype: Mapped[Optional[str]] = mapped_column(String(20))
    size_bytes: Mapped[Optional[int]]
    checksum: Mapped[Optional[str]] = mapped_column(String(64))  # md5/sha256
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # N-N com Strategy
    strategies: Mapped[List["Strategy"]] = relationship(
        "Strategy",
        secondary="strategy_uploads",
        back_populates="uploads",
        lazy="selectin",
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "owner": self.owner,
            "filename": self.filename,
            "path": self.path,
            "filetype": self.filetype,
            "size_bytes": self.size_bytes,
            "checksum": self.checksum,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# ------------ Tabela de associação (N-N) ------------
class StrategyUpload(Base):
    __tablename__ = "strategy_uploads"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)
    upload_id: Mapped[int]   = mapped_column(ForeignKey("uploads.id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        UniqueConstraint("strategy_id", "upload_id", name="uq_strategy_upload"),
    )


# ------------ Insight (1-N a Strategy) ------------
class Insight(Base):
    __tablename__ = "insights"

    id: Mapped[int] = mapped_column(primary_key=True)
    strategy_id: Mapped[int] = mapped_column(ForeignKey("strategies.id", ondelete="CASCADE"), nullable=False)

    title: Mapped[str] = mapped_column(String(200), nullable=False)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    metrics_json: Mapped[Optional[str]] = mapped_column(Text)
    artifact_path: Mapped[Optional[str]] = mapped_column(String(1024))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    strategy: Mapped["Strategy"] = relationship("Strategy", back_populates="insights")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "title": self.title,
            "summary": self.summary,
            "metrics_json": self.metrics_json,
            "artifact_path": self.artifact_path,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
