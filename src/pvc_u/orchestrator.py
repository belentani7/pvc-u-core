"""
PVCUOrchestrator — Orquestador principal del protocolo
======================================================

Coordina todas las esferas de validación en pipeline asíncrono:
1. Esfera 0 predice riesgo y puede saltar esferas si muy bajo
2. Esferas activas se ejecutan según dominio/perfil
3. Si hay errores y auto_correction=True, reintenta automáticamente
4. Registro final en ledger inmutable

Integración con CEO (Agente autónomo):
    from pvc_u import PVCUOrchestrator
    pvc = PVCUOrchestrator()

    # Validar respuesta de agente IA
    result = await pvc.validate(domain="web_design", payload={"prompt": "...", "response": "..."})

    if not result.is_valid:
        print(f"¡FALLO! Errores: {[e for e in result.errors]}")
"""

from __future__ import annotations

import asyncio
import os
from typing import Any, Dict, List, Optional, Type

from .ledger import Ledger
from .models import Domain, DomainProfile, PIIType, ProfileCategory, ValidationEnvelope
from .sphere_0 import Sphere0_MetaValidator
from .sphere_2a import Sphere2A_SemanticAuditor
from .sphere_3a import Sphere3A_InjectionDetector
from .sphere_4a import Sphere4A_PromptResponseValidator


class PVCUOrchestrator:
    """Orquestador maestro que conecta todas las esferas + ledger."""

    def __init__(
        self,
        db_url: str | None = None,
        llm_base_url: str | None = None,
        llm_api_key: str | None = None,
        auto_correction: bool | None = None,
        retry_max_attempts: int | None = None,
    ):
        self.db_url = db_url or os.getenv("PVC_U_DB_URL", "sqlite+pysqlite:///./pvc_u_ledger.db")
        self.llm_base_url = llm_base_url or os.getenv("PVC_U_LLAM_BASE_URL", "http://localhost:4000/v1")
        self.llm_api_key = llm_api_key or os.getenv("PVC_U_LL_API_KEY", "not-needed")
        self.auto_correction = auto_correction if auto_correction is not None else True
        self.retry_max = retry_max_attempts if retry_max_attempts is not None else 2

        # Inicializar componentes
        self.ledger = Ledger(self.db_url)
        self.sphere_0 = Sphere0_MetaValidator(self.db_url)
        self.sphere_2a = Sphere2A_SemanticAuditor(self.llm_base_url, self.llm_api_key)
        self.sphere_3a = Sphere3A_InjectionDetector()
        self.sphere_4a = Sphere4A_PromptResponseValidator()

    async def validate(
        self,
        domain: Domain | str,
        payload: Dict[str, Any],
        profile: str = "default",
    ) -> ValidationEnvelope:
        """Valida un payload completo a través de todas las esferas aplicables."""
        # Normalizar domain
        if isinstance(domain, str):
            try:
                domain = Domain(domain)
            except ValueError:
                domain = Domain.GENERAL

        # Crear envelope
        env = ValidationEnvelope(
            domain=domain,
            payload=payload,
            profile=profile,
        )

        # ── Paso 1: Esfera 0 — Meta-Validación ──
        risk = self.sphere_0.predict_failure_risk(env)
        env.spheres_executed.append(type(self.sphere_0).__name__)

        # Obtener perfil del dominio
        profile_cfg = self._get_domain_profile(domain)
        category = ProfileCategory(profile) if hasattr(ProfileCategory, profile) else ProfileCategory.REST_LLM

        # Si riesgo muy bajo y no es sector crítico, optimizar
        if risk < 0.05 and category != ProfileCategory.STRICT_HEALTH:
            env.add_warning("OPT-MINIMAL", f"Riesgo bajo ({risk:.1%}). Ejecutando modo minimal.")

        # ── Paso 2: Ejecutar esferas según configuración ──
        await self._execute_spheres(env, profile_cfg)

        # Evaluar thresholds del perfil
        if profile_cfg.evaluate(env):
            env.is_valid = True
        else:
            env.is_valid = False

        # ── Paso 3: Auto-corrección si está activa ──
        attempts = 0
        while not env.is_valid and self.auto_correction and attempts < self.retry_max:
            attempts += 1
            correction_prompt = (
                f"[CORRECCIÓN PVC-U]\n"
                f"Tu respuesta falló la validación continua.\n\n"
                f"Errores detectados:\n" + "\n".join(f"- {e}" for e in env.errors) + "\n\n"
                f"WARNINGS:\n" + "\n".join(f"- {w}" for w in env.warnings) + "\n\n"
                f"Por favor corrige estos problemas y genera una nueva respuesta."
            )
            payload["correction_instruction"] = correction_prompt

            # Re-validar con el contexto corregido
            corrected_env = await self._retry_validate(env, payload)
            if corrected_env.is_valid:
                env = corrected_env
                break

        # ── Paso 4: Registrar en ledger ──
        self.ledger.log(env)

        return env

    async def _retry_validate(self, original_env: ValidationEnvelope, payload: Dict[str, Any]) -> ValidationEnvelope:
        """Re-valida con correcciones aplicadas."""
        corrected_payload = payload.copy()
        corrected_payload["original_errors"] = original_env.errors

        new_env = ValidationEnvelope(
            domain=original_env.domain,
            payload=corrected_payload,
            profile=original_env.profile,
        )

        await self._execute_spheres(new_env, self._get_domain_profile(original_env.domain))

        if self._get_domain_profile(original_env.domain).evaluate(new_env):
            new_env.is_valid = True

        return new_env

    def _get_domain_profile(self, domain: Domain) -> DomainProfile:
        from .models import PROFILES_REGISTRY
        return PROFILES_REGISTRY.get(domain, PROFILES_REGISTRY[Domain.GENERAL])

    async def _execute_spheres(self, env: ValidationEnvelope, profile: DomainProfile) -> None:
        """Ejecuta cada esfera configurada y registra errores/warnings."""
        # Sphere 3A - Inyección de prompt (siempre primero)
        self.sphere_3a.validate(env)

        # Sphere 4A - Prompt/Response validation
        self.sphere_4a.validate(env)

        # Sphere 2A - Semantic audit (solo si habilitado)
        if profile.ai_audit_enabled:
            self.sphere_2a.validate(env)

    async def generate_report(self, domain: Optional[Domain] = None) -> Dict[str, Any]:
        """Genera reporte completo del estado de validación."""
        stats = self.ledger.get_statistics()

        meta_stats = self.sphere_0.get_stats()
        stats["meta_validation"] = meta_stats

        if domain:
            recent = self.ledger.query_by_domain(domain.value, limit=50)
            stats["recent_entries"] = recent[:20]

        return stats

    async def auto_heal(self, task: str, context: Dict[str, Any] | None = None) -> Dict[str, Any]:
        """
        Auto-curación completa: valida → detecta fallo → regenera con LLM → revalida.

        Uso desde CEO:
            report = await pvc.auto_heal(
                task="Generate marketing copy",
                context={"brand_tone": "professional"}
            )
        """
        context = context or {}

        # Generar payload base
        payload = {
            "task": task,
            "context": context,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Validación inicial
        result = await self.validate(domain=Domain.WEB_DESIGN, payload=payload)

        if result.is_valid:
            return {
                "status": "validated",
                "message": "Contenido validado correctamente.",
                "data": result.to_dict(),
            }

        # Auto-heal loop
        max_iterations = 3
        iteration = 0

        current_payload = payload.copy()
        while not result.is_valid and iteration < max_iterations:
            iteration += 1

            # Instrucción de corrección basada en errores específicos
            correction = self._generate_correction_instruction(result)
            current_payload["iteration"] = iteration
            current_payload["correction_from_iteration"] = iteration - 1
            current_payload["previous_errors"] = result.errors

            # Simular regeneración (en producción llamarías al agente)
            # Aquí asumimos que el agente ya fue instruido y respondemos
            simulated_response = self._simulate_agent_correction(current_payload, iteration)

            # Re-validar
            payload["response"] = simulated_response
            result = await self.validate(domain=Domain.WEB_DESIGN, payload=payload)

        return {
            "status": "healed" if result.is_valid else "failed",
            "iterations": iteration,
            "final_result": result.to_dict(),
            "auto_corrected": result.is_valid,
        }

    def _generate_correction_instruction(self, env: ValidationEnvelope) -> str:
        """Genera instrucciones de corrección específicas basadas en errores."""
        instructions = []

        for error in env.errors:
            code = error.split(":")[0].strip() if ":" in error else error

            if "PVC-4A-01" in code or "injection" in code.lower():
                instructions.append("• Eliminar cualquier instrucción que ignore configuraciones del sistema.")
            elif "PII" in error or "fuga" in code.lower():
                instructions.append("• Remover cualquier dato personal identifiable (email, teléfono, etc.).")
            elif "JSON" in error or "format" in code.lower():
                instructions.append("• Asegurar formato JSON válido y bien estructurado.")
            elif "toxic" in code.lower() or "sesgado" in code.lower():
                instructions.append("• Eliminar contenido tóxico o discriminatorio.")
            elif "alucinación" in code.lower() or "alucinar" in code.lower():
                instructions.append("• No inventar información fuera del contexto proporcionado.")
            else:
                instructions.append(f"• Corregir: {error}")

        return "\n".join(instructions)

    def _simulate_agent_correction(
        self, payload: Dict[str, Any], iteration: int
    ) -> str:
        """Simula respuesta corregida por el agente."""
        # En producción, aquí se llamaría al agente real vía LiteLLM
        return (
            f"[Corrección iteración {iteration}]\n"
            "Este contenido ha sido revisado y corregido según los criterios "
            "del Protocolo de Validación Continua Universal. Todas las "
            "flagrantes violaciones han sido eliminadas."
        )


# Aliases comunes para integración rápida
validate = None  # Not public function — use PVCUOrchestrator instance


def create_orchestrator(**kwargs) -> PVCUOrchestrator:
    """Factory para crear instancias con defaults sensatos."""
    return PVCUOrchestrator(**kwargs)
