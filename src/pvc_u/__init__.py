"""
PVC-U — Protocolo de Validación Continua Universal
===================================================

Kernel de gobernanza para Empresas de IA Autónomas de Nivel Empresarial.

Stack: Python 3.10+ / FastAPI / PostgreSQL / Pydantic v2 / LiteLLM
License: MIT

Autor: Pedro Belentani (belentani7)
Fecha: 2026-09-03
"""

from .models import (
    Domain,
    DomainProfile,
    ProfileCategory,
    PIIType,
    ValidationEnvelope,
    PVCUConfig,
)
from .sphere_0 import Sphere0_MetaValidator
from .sphere_2a import Sphere2A_SemanticAuditor
from .sphere_3a import Sphere3A_InjectionDetector
from .sphere_4a import Sphere4A_PromptResponseValidator
from .sphere_4a_enhanced import Sphere4A_EnhancedValidator
from .ledger import Ledger, LedgerEntry
from .orchestrator import PVCUOrchestrator, create_orchestrator
from .metrics import VALIDATION_REQUESTS, record_validation, get_metrics


__version__ = "1.0.1"
__all__ = [
    # Models
    "Domain",
    "DomainProfile",
    "ProfileCategory",
    "PIIType",
    "ValidationEnvelope",
    "PVCUConfig",
    # Spheres
    "Sphere0_MetaValidator",
    "Sphere2A_SemanticAuditor",
    "Sphere3A_InjectionDetector",
    "Sphere4A_PromptResponseValidator",
    "Sphere4A_EnhancedValidator",
    # Ledger
    "Ledger",
    "LedgerEntry",
    # Orchestrator
    "PVCUOrchestrator",
    "create_orchestrator",
    # Metrics
    "VALIDATION_REQUESTS",
    "record_validation",
    "get_metrics",
]
