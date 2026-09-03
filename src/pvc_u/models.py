"""
PVC-U Core Models
==================

Entidades centrales del protocolo: ValidationEnvelope, DomainProfile, SphereConfig.
"""

from __future__ import annotations

import json
import os
import hashlib
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SphereID(str, Enum):
    """IDs de sub-esferas de validación."""
    SPHERE_4A_PROMPT_RESPONSE = "sphere-4a-prompt-response"
    SPHERE_2A_BEHAVIOR = "sphere-2a-behavior"
    SPHERE_3A_INJECTION = "sphere-3a-injection"
    SPHERE_5A_COMPLIANCE = "sphere-5a-compliance"
    SPHERE_6A_DATA_GOVERNANCE = "sphere-6a-data-governance"


class PIIType(str, Enum):
    """Tipos de PII para detección."""
    EMAIL = "email"
    PHONE = "phone"
    CREDIT_CARD = "credit_card"
    SSN = "ssn"
    IP_ADDRESS = "ip_address"
    API_KEY = "api_key"


class Domain(str, Enum):
    """Dominios regulatorios soportados."""
    ECOMMERCE = "ecommerce"
    SALUD = "salud"
    FINANZAS = "finanzas"
    WEB_DESIGN = "web_design"
    CHATBOT = "chatbot"
    GENERAL = "general"


class ProfileCategory(str, Enum):
    """Categorías de perfil de compliance."""
    REST_LLM = "rest+llm"
    FHIR_HIPAA = "fhir+hipaa"
    PCI_DSS = "pci-dss"
    GDPR = "gdpr"
    STRICT_HEALTH = "health"
    STRICT_FINANCE = "finance"


# ---------------------------------------------------------------------------
# Validation Envelope
# ---------------------------------------------------------------------------

class ValidationEnvelope(BaseModel):
    """Envoltorio inmutable que contiene toda la información de validación."""

    id: str = Field(default_factory=lambda: hashlib.sha256(os.urandom(32)).hexdigest()[:16])
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    domain: Domain
    payload: Dict[str, Any]  # Prompt + response + metadata de IA
    profile: str
    is_valid: bool = False
    errors: List[str] = []
    warnings: List[str] = []
    meta_validation_score: Optional[float] = None
    spheres_executed: List[SphereID] = []
    risk_assessment: float = 0.5  # Score 0-1 calculado por Esfera 0

    @field_validator("payload", mode="before")
    @classmethod
    def ensure_payload_dict(cls, v: Any) -> Dict:
        """Asegura que payload siempre es un dict serializable."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return {"raw": v}
        if not isinstance(v, dict):
            return {"raw": str(v)}
        return v

    @property
    def prompt(self) -> Optional[str]:
        return self.payload.get("prompt")

    @property
    def response(self) -> Optional[str]:
        return self.payload.get("response")

    @property
    def expected_format(self) -> Optional[str]:
        return self.payload.get("expected_format")

    def add_error(self, code: str, message: str) -> None:
        self.errors.append(f"{code}: {message}")

    def add_warning(self, code: str, message: str) -> None:
        self.warnings.append(f"W-{code}: {message}")

    def to_json(self, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "domain": self.domain.value,
            "profile": self.profile,
            "payload": self.payload,
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "meta_validation_score": self.meta_validation_score,
            "spheres_executed": [s.value for s in self.spheres_executed],
            "risk_assessment": self.risk_assessment,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ValidationEnvelope":
        data.pop("model", None)  # Ignorar si viene en JSON
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> "ValidationEnvelope":
        return cls.from_dict(json.loads(json_str))


# ---------------------------------------------------------------------------
# Ledger Entry
# ---------------------------------------------------------------------------

class LedgerEntry(BaseModel):
    """Registro inmutable para auditoría continua."""

    id: str
    envelope_id: str
    timestamp: str
    domain: str
    is_valid: bool
    error_count: int
    score: Optional[float]
    risk_percent: float
    checksum: str

    @staticmethod
    def compute_checksum(data: Dict[str, Any]) -> str:
        """Checksum SHA-256 para verificar integridad."""
        canonical = json.dumps(data, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    def compute_entry_hash(self) -> str:
        return self.compute_checksum({
            "id": self.id,
            "envelope_id": self.envelope_id,
            "timestamp": self.timestamp,
            "domain": self.domain,
            "is_valid": self.is_valid,
        })


# ---------------------------------------------------------------------------
# Domain Configuration (Profiles + Thresholds)
# ---------------------------------------------------------------------------

class ComplianceThreshold(BaseModel):
    """Umbral mínimo de confianza por dominio."""
    min_score: float = 0.8
    max_errors: int = 3
    block_on_warnings: bool = False

    def evaluate(self, env: ValidationEnvelope) -> bool:
        if env.meta_validation_score and env.meta_validation_score < self.min_score:
            return False
        max_err = self.max_errors
        if self.block_on_warnings:
            max_err = 0  # Cualquier warning bloquea
        return len(env.errors) <= max_err


class DomainProfile(BaseModel):
    """Perfil de compliance completo para un dominio regulatorio."""

    domain: Domain
    category: ProfileCategory
    thresholds: ComplianceThreshold
    required_spheres: List[SphereID] = []
    pii_detection_enabled: bool = True
    injection_detection_enabled: bool = True
    ai_audit_enabled: bool = True
    description: str = ""

    def __hash__(self):
        return hash(self.domain.value)

    def evaluate(self, env: ValidationEnvelope) -> bool:
        return self.thresholds.evaluate(env)


# ─── Per-Domain Profiles Registry ──────────────────────────────────────

PROFILES_REGISTRY: Dict[Domain, DomainProfile] = {
    Domain.ECOMMERCE: DomainProfile(
        domain=Domain.ECOMMERCE,
        category=ProfileCategory.REST_LLM,
        thresholds=ComplianceThreshold(min_score=0.7, max_errors=3),
        pii_detection_enabled=True,
        injection_detection_enabled=True,
        ai_audit_enabled=False,
        description="E-commerce estándar — protección básica contra fuga de datos e inyección.",
    ),
    Domain.SALUD: DomainProfile(
        domain=Domain.SALUD,
        category=ProfileCategory.FHIR_HIPAA,
        thresholds=ComplianceThreshold(min_score=0.95, max_errors=0, block_on_warnings=True),
        pii_detection_enabled=True,
        injection_detection_enabled=True,
        ai_audit_enabled=True,
        description="Salud (HIPAA/FHIR) — ultra-estricto: 0 errores permitidos, 0 warnings.",
    ),
    Domain.FINANZAS: DomainProfile(
        domain=Domain.FINANZAS,
        category=ProfileCategory.PCI_DSS,
        thresholds=ComplianceThreshold(min_score=0.9, max_errors=1, block_on_warnings=True),
        pii_detection_enabled=True,
        injection_detection_enabled=True,
        ai_audit_enabled=True,
        description="Finanzas (PCI-DSS) — muy estricto: máximo 1 error, sin warnings.",
    ),
    Domain.WEB_DESIGN: DomainProfile(
        domain=Domain.WEB_DESIGN,
        category=ProfileCategory.REST_LLM,
        thresholds=ComplianceThreshold(min_score=0.5, max_errors=5),
        pii_detection_enabled=False,
        injection_detection_enabled=False,
        ai_audit_enabled=False,
        description="Web design — relajado, orientado a creatividad.",
    ),
    Domain.CHATBOT: DomainProfile(
        domain=Domain.CHATBOT,
        category=ProfileCategory.GDPR,
        thresholds=ComplianceThreshold(min_score=0.75, max_errors=2),
        pii_detection_enabled=True,
        injection_detection_enabled=True,
        ai_audit_enabled=True,
        description="Chatbot genérico con GDPR básico.",
    ),
    Domain.GENERAL: DomainProfile(
        domain=Domain.GENERAL,
        category=ProfileCategory.REST_LLM,
        thresholds=ComplianceThreshold(min_score=0.5, max_errors=5),
        pii_detection_enabled=True,
        injection_detection_enabled=False,
        ai_audit_enabled=False,
        description="General / default — balance entre seguridad y flexibilidad.",
    ),
}


# ---------------------------------------------------------------------------
# CLI & Config Models
# ---------------------------------------------------------------------------

class PVCUConfig(BaseModel):
    """Configuración principal del sistema PVC-U."""

    db_url: str = "sqlite+pysqlite:///./pvc_u_ledger.db"
    llm_api_base: str = "http://localhost:4000/v1"
    llm_api_key: str = "sk-not-needed-local"
    llm_model: str = "groq/llama-3.1-8b-instant"
    audit_enabled: bool = True
    auto_correction: bool = True
    retry_max_attempts: int = 2
    enable_domain_profiles: bool = True

    @property
    def config_path(self) -> Path:
        return Path(__file__).parent.parent.parent / "config" / "pvcu.json"

    def save(self, path: Optional[Path] = None) -> None:
        p = path or self.config_path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "PVCUConfig":
        p = path or cls._default_config_path()
        if p.exists():
            return cls.model_validate_json(p.read_text())
        return cls()

    @staticmethod
    def _default_config_path() -> Path:
        home = Path.home() / ".pvcu"
        home.mkdir(exist_ok=True)
        return home / "config.json"


# ---------------------------------------------------------------------------
# Init helpers
# ---------------------------------------------------------------------------

def create_default_config() -> Path:
    """Crea config.json con valores defaults en ~/.pvcu/config.json"""
    cfg = PVCUConfig()
    cfg.save()
    return cfg.config_path
