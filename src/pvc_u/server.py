"""
FastAPI Server — API REST para PVC-U
=====================================

Endpoints:
  POST /v1/validate      - Validar payload completo
  GET  /v1/report        - Generar reporte del estado
  POST /v1/auto-heal     - Auto-corrección iterativa
  GET  /v1/stats         - Estadísticas globales
  GET  /health           - Healthcheck para Docker/K8s

Uso:
    uvicorn pvc_u.server:app --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .models import Domain
from .orchestrator import PVCUOrchestrator

# ──────────────── Pydantic Models para API ──────────────────────

class ValidateRequest(BaseModel):
    domain: str = Field(..., description="Dominio regulatorio")
    prompt: str = Field(..., description="Prompt original enviado al agente IA")
    response: str = Field(..., description="Respuesta del agente a validar")
    profile: str = Field(default="default", description="Perfil de compliance")


class ValidateResponse(BaseModel):
    valid: bool
    errors: List[str]
    warnings: List[str]
    score: float
    risk_percent: float
    spheres_executed: List[str]


class HealRequest(BaseModel):
    task: str = Field(..., description="Tarea completa a auto-curar")
    context: Dict[str, Any] = Field(default_factory=dict, description="Contexto adicional")


class ReportResponse(BaseModel):
    total_entries: int
    validation_rate: float
    avg_score: float
    by_domain: List[Dict[str, Any]]


# ──────────────── FastAPI App ────────────────────────────────────

app = FastAPI(
    title="PVC-U API",
    description="Protocolo de Validación Continua Universal — Enterprise AI Governance",
    version="1.0.0",
)

# Instancia global del orquestador (se inicializa en startup)
pvc_orchestrator: Optional[PVCUOrchestrator] = None


@app.on_event("startup")
async def startup():
    global pvc_orchestrator
    from os import getenv
    pvc_orchestrator = PVCUOrchestrator(
        db_url=getenv("PVC_U_DB_URL", "sqlite+pysqlite:///./pvc_u_ledger.db"),
        llm_base_url=getenv("PVC_U_LLAM_BASE_URL", "http://localhost:4000/v1"),
        llm_api_key=getenv("PVC_U_LL_API_KEY", "not-needed"),
        auto_correction=True,
    )


@app.get("/health", summary="Healthcheck para Docker/Kubernetes")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
    }


@app.post("/v1/validate", response_model=ValidateResponse, summary="Validar respuesta de agente IA")
async def validate(request: ValidateRequest):
    """
    Valida una respuesta de agente IA contra las esferas PVC-U completas.
    
    Detecta: inyección de prompt, fuga de PII, formato inválido, toxicidad.
    """
    if not pvc_orchestrator:
        raise HTTPException(503, "Servicio no iniciado")
    
    try:
        env = await pvc_orchestrator.validate(
            domain=request.domain,
            payload={"prompt": request.prompt, "response": request.response},
            profile=request.profile,
        )
        
        return ValidateResponse(
            valid=env.is_valid,
            errors=env.errors,
            warnings=env.warnings,
            score=env.meta_validation_score or 0.5,
            risk_percent=env.risk_assessment * 100,
            spheres_executed=[type(s).__name__ for s in [
                pvc_orchestrator.sphere_0,
                pvc_orchestrator.sphere_3a,
                pvc_orchestrator.sphere_4a,
            ]],
        )
    except Exception as exc:
        raise HTTPException(500, f"Error de validación: {str(exc)}")


@app.post("/v1/auto-heal", summary="Auto-corrección iterativa con LLM")
async def auto_heal(request: HealRequest):
    """
    Valida → detecta fallo → regenera con LLM → revalida automáticamente.
    
    Ideal para integración con CEO de agencia autónoma.
    """
    if not pvc_orchestrator:
        raise HTTPException(503, "Servicio no iniciado")
    
    try:
        result = await pvc_orchestrator.auto_heal(
            task=request.task,
            context=request.context,
        )
        
        return {
            "status": result["status"],
            "iterations": result["iterations"],
            "auto_corrected": result["auto_corrected"],
            "final_result": result["final_result"],
        }
    except Exception as exc:
        raise HTTPException(500, f"Error en auto-heal: {str(exc)}")


@app.get("/v1/report", response_model=ReportResponse, summary="Reporte del estado de validación")
async def report():
    """Genera reporte completo con estadísticas del ledger."""
    if not pvc_orchestrator:
        raise HTTPException(503, "Servicio no iniciado")
    
    stats = await pvc_orchestrator.generate_report()
    
    return ReportResponse(
        total_entries=stats.get("total_entries", 0),
        validation_rate=stats.get("validation_rate", 0),
        avg_score=stats.get("avg_meta_score", 0),
        by_domain=stats.get("by_domain", []),
    )


@app.get("/v1/stats", summary="Estadísticas globales del sistema")
async def stats():
    """Devuelve métricas completas del protocolo."""
    if not pvc_orchestrator:
        raise HTTPException(503, "Servicio no iniciado")
    
    full_stats = await pvc_orchestrator.generate_report()
    meta_stats = pvc_orchestrator.sphere_0.get_stats()
    
    return {
        "ledger_stats": full_stats,
        "meta_validation": meta_stats,
    }
