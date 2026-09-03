"""
PVC-U — Protocolo de Validación Continua Universal
===================================================

Kernel de gobernanza para Empresas de IA Autónomas de Nivel Empresarial.

Garantiza que la IA no alucina, no filtra datos y cumple normativa regulatoria.

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
from .ledger import Ledger, LedgerEntry
from .orchestrator import PVCUOrchestrator, create_orchestrator

__version__ = "1.0.0"
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
    # Ledger
    "Ledger",
    "LedgerEntry",
    # Orchestrator
    "PVCUOrchestrator",
    "create_orchestrator",
]

# Quick API check — if installed properly, this works:
# from pvc_u import PVCUOrchestrator
# pvc = PVCUOrchestrator()
# result = await pvc.validate(domain="ecommerce", payload={"prompt": "...", "response": "..."})
