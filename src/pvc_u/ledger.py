"""
Ledger — Base de datos inmutable para auditoría continua
=========================================================

Soporta SQLite y PostgreSQL mediante SQLAlchemy.
Cada entrada tiene checksum SHA-256 para verificar integridad.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite
from sqlalchemy import Column, String, Integer, Text, Float, DateTime, func, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


Base = declarative_base()


class LedgerEntry(Base):
    """Modelo SQLAlchemy para registro en ledger."""

    __tablename__ = "ledger"

    id = Column(String(16), primary_key=True)
    envelope_id = Column(String(16), nullable=False, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    domain = Column(String(50), nullable=False, index=True)
    payload_preview = Column(Text, nullable=True)  # Primeros 1000 chars del payload
    profile = Column(String(50), nullable=False)
    is_valid = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    meta_score = Column(Float, nullable=True)
    risk_assessment = Column(Float, default=0.5)
    checksum = Column(String(16), nullable=False)
    spheres_executed = Column(Text, default="[]")
    entry_hash = Column(String(64), unique=True, nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "envelope_id": self.envelope_id,
            "timestamp": self.timestamp.isoformat(),
            "domain": self.domain,
            "profile": self.profile,
            "is_valid": bool(self.is_valid),
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "meta_score": self.meta_score,
            "risk_assessment": self.risk_assessment,
            "checksum": self.checksum,
        }


class Ledger:
    """Ledger inmutable con soporte SQLite/PostgreSQL."""

    def __init__(self, db_url: str = "sqlite+pysqlite:///./pvc_u_ledger.db"):
        self.db_url = db_url
        self._engine = None
        self._async_engine = None
        self._ensure_tables()

    def _get_engine(self):
        if self._engine is None:
            self._engine = create_engine(self.db_url)
        return self._engine

    @staticmethod
    def compute_checksum(data: Dict[str, Any]) -> str:
        """Checksum SHA-256 para verificar integridad."""
        canonical = json.dumps(data, sort_keys=True).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()[:16]

    @staticmethod
    def compute_entry_hash(entry: Dict[str, Any]) -> str:
        """Hash completo del entry para blockchain-like verification."""
        essential = {k: entry.get(k) for k in ["id", "envelope_id", "timestamp", "domain", "is_valid"]}
        return hashlib.sha256(json.dumps(essential, sort_keys=True).encode()).hexdigest()

    def _ensure_tables(self) -> None:
        engine = self._get_engine()
        Base.metadata.create_all(engine)

    def log(self, env) -> None:
        """Registra un ValidationEnvelope en el ledger."""
        from .models import ValidationEnvelope

        if not isinstance(env, ValidationEnvelope):
            raise TypeError(f"Expected ValidationEnvelope, got {type(env).__name__}")

        preview_len = min(len(str(env.payload)), 1000)
        preview = str(env.payload)[:preview_len]

        check_data = {
            "envelope_id": env.id,
            "timestamp": str(env.timestamp),
            "domain": env.domain.value if hasattr(env.domain, "value") else str(env.domain),
            "is_valid": bool(env.is_valid),
        }

        entry = LedgerEntry(
            id=env.id,
            envelope_id=env.id,
            timestamp=env.timestamp,
            domain=env.domain.value if hasattr(env.domain, "value") else str(env.domain),
            payload_preview=preview,
            profile=env.profile,
            is_valid=int(env.is_valid),
            error_count=len(env.errors),
            warning_count=len(env.warnings),
            meta_score=env.meta_validation_score,
            risk_assessment=env.risk_assessment,
            checksum=self.compute_checksum(check_data),
            spheres_executed=json.dumps([s.value for s in env.spheres_executed]),
            entry_hash=self.compute_entry_hash(check_data),
        )

        session = sessionmaker(bind=self._get_engine)()
        session.add(entry)
        session.commit()
        session.close()

    def query_by_domain(self, domain: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Consulta últimos N registros por dominio."""
        session = sessionmaker(bind=self._get_engine)()
        results = (
            session.query(LedgerEntry)
            .filter(LedgerEntry.domain == domain)
            .order_by(LedgerEntry.timestamp.desc())
            .limit(limit)
            .all()
        )
        session.close()
        return [entry.to_dict() for entry in results]

    def get_statistics(self) -> Dict[str, Any]:
        """Devuelve estadísticas globales del ledger."""
        session = sessionmaker(bind=self._get_engine)()

        total = session.query(func.count(LedgerEntry.id)).scalar() or 0
        valid = (
            session.query(func.count(LedgerEntry.id))
            .filter(LedgerEntry.is_valid == 1)
            .scalar()
            or 0
        )
        invalid = total - valid

        avg_score = (
            session.query(func.avg(LedgerEntry.meta_score))
            .filter(LedgerEntry.meta_score.isnot(None))
            .scalar()
            or 0
        )

        # Por dominio
        domain_stats = (
            session.query(
                LedgerEntry.domain,
                func.count(LedgerEntry.id).label("total"),
                func.sum(LedgerEntry.is_valid).label("valid"),
            )
            .group_by(LedgerEntry.domain)
            .all()
        )

        session.close()

        return {
            "total_entries": total,
            "valid": valid,
            "invalid": invalid,
            "validation_rate": round(valid / max(total, 1) * 100, 1),
            "avg_meta_score": round(avg_score or 0, 3),
            "by_domain": [
                {"domain": d.domain, "total": d.total, "valid": d.valid or 0}
                for d in domain_stats
            ],
        }
