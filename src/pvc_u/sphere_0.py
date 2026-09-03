"""
Sphère 0 — Meta-Validador Predictivo
====================================

Predice la probabilidad de fallo antes de ejecutar esferas costosas.
Usa el historial del Ledger para calcular un score de riesgo por dominio.

Cuando el riesgo es muy bajo (<5%) y el perfil no es "health", se pueden omitir
esferas caras con registro en ledger (optimización de costos).
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import ValidationEnvelope, Domain


class Sphere0_MetaValidator:
    """Meta-Validador que predice probabilidad de fallo usando el Ledger histórico."""

    def __init__(self, db_path: str = "pvc_u_ledger.db"):
        self.db_path = db_path
        self._ensure_table()

    def _ensure_table(self) -> None:
        """Asegura que existe la tabla de métricas de entrenamiento."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS meta_metrics (
                    domain TEXT NOT NULL,
                    total_validated INTEGER DEFAULT 0,
                    total_errors INTEGER DEFAULT 0,
                    last_updated TEXT
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def predict_failure_risk(self, env: ValidationEnvelope) -> float:
        """
        Predice el riesgo basado en fallos históricos del dominio.

        Returns: float entre 0 y 1 donde 1 = riesgo máximo.
        """
        risk = self._calculate_from_history(env.domain)
        env.risk_assessment = risk
        return risk

    def _calculate_from_history(self, domain: Domain) -> float:
        """Calcula riesgo desde el historial de validaciones."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.cursor()

            # Intentar obtener métricas agregadas primero
            cursor.execute(
                "SELECT total_validated, total_errors FROM meta_metrics WHERE domain = ?",
                (domain.value,),
            )
            row = cursor.fetchone()

            if row and row[0] > 0:
                total, errors = row
                return min(errors / total, 1.0)

            # Fallback: contar desde el ledger completo
            cursor.execute(
                """
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN is_valid = 0 THEN 1 ELSE 0 END) as errors
                FROM ledger WHERE domain = ?
                """,
                (domain.value,),
            )
            row = cursor.fetchone()

            if row and row[0] > 0:
                total, errors = row
                risk = (errors or 0) / max(total, 1)
                # Guardar métricas para futuro
                self._update_metrics(domain, int(row[0] or 0), int(row[1] or 0))
                return risk

            return 0.5  # Riesgo neutro si no hay historial

        finally:
            conn.close()

    def _update_metrics(self, domain: Domain, total: int, errors: int) -> None:
        """Actualiza o inserta las métricas agregadas."""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """
                INSERT INTO meta_metrics (domain, total_validated, total_errors, last_updated)
                VALUES (?, ?, ?, datetime('now'))
                ON CONFLICT(domain) DO UPDATE SET
                    total_validated = excluded.total_validated,
                    total_errors = excluded.total_errors,
                    last_updated = excluded.last_updated
                """,
                (domain.value, total, errors),
            )
            conn.commit()
        finally:
            conn.close()

    def get_stats(self) -> Dict[str, Any]:
        """Devuelve estadísticas globales de todos los dominios."""
        conn = sqlite3.connect(self.db_path)
        try:
            cursor = conn.execute(
                """
                SELECT domain, total_validated, total_errors,
                       ROUND(CAST(total_errors AS REAL) / NULLIF(total_validated, 0) * 100, 1) as error_rate
                FROM meta_metrics
                ORDER BY error_rate DESC
                """
            )
            rows = cursor.fetchall()
            return {
                "meta_stats": [
                    {
                        "domain": r[0],
                        "validated": r[1],
                        "errors": r[2],
                        "error_rate_percent": r[3] or 0,
                    }
                    for r in rows
                ]
            }
        finally:
            conn.close()
