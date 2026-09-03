#!/usr/bin/env python3
"""
Ejemplo: Integración de PVC-U con CEO (Agente Autónomo)
=========================================================

Integra validación continua en el flujo de un CEO que orquesta agentes
como MiMo Code, Aider y OpenCode (ocx).

Este es el patrón real que usarías en producción para vender
el servicio "Agencia Cero-Alucinación" a clientes enterprise.
"""

import asyncio
import subprocess
import os
from typing import Dict, Any, Optional


# Importar PVC-U
try:
    from pvc_u import PVCUOrchestrator, Domain
except ImportError:
    # Fallback: si no está instalado, simular estructura
    print("[WARN] PVC-U no instalado — ejecutando en modo demo")
    PVCUOrchestrator = None


class AgencyCEO:
    """
    CEO simulado que valida TODO antes de entregar al cliente.
    
    Patrón empresarial:
    1. Recibe task del cliente
    2. Descompone en subtareas
    3. Asigna a agentes especializados
    4. VALIDA cada respuesta con PVC-U ANTES de devolver
    5. Auto-corrige si hay errores
    """
    
    def __init__(self):
        self.pvc = PVCUOrchestrator(
            db_url="sqlite+pysqlite:///./ceo_ledger.db",
            auto_correction=True,
            retry_max_attempts=3,
        )
        
        self.agents = {
            "coder": "mimo",      # MiMo Code para código
            "qa": "aider",        # Aider para tests/security  
            "designer": "ocx",    # OpenCodeX para frontend
        }
    
    async def execute_task(self, client_task: str, domain: Domain = Domain.ECOMMERCE) -> Dict[str, Any]:
        """Ejecuta una tarea completa con validación continua."""
        print(f"\n[CEO] Task recibido: {client_task}")
        
        # Paso 1: Descomponer (en producción, usarías LLM aquí)
        subtasks = [
            {"role": "coder", "prompt": f"Crea API REST para {client_task}", "domain": domain},
            {"role": "qa", "prompt": f"Escribe tests para {client_task}", "domain": domain},
            {"role": "designer", "prompt": f"Diseña UI para {client_task}", "domain": domain},
        ]
        
        results = {}
        
        for i, subtask in enumerate(subtasks, 1):
            print(f"[CEO] Ejecutando subtask {i}/{len(subtasks)}...")
            
            # Ejecutar agente
            agent_result = self._run_agent(subtask["role"], subtask["prompt"])
            
            # VALIDAR con PVC-U
            envelope = await self.pvc.validate(
                domain=subtask["domain"],
                payload={
                    "agent": subtask["role"],
                    "prompt": subtask["prompt"],
                    "response": agent_result[:500],  # Primeros 500 chars
                },
            )
            
            if not envelope.is_valid:
                print(f"[PVC-U] ⚠️ FALLÓ validación ({len(envelope.errors)} errores)")
                print(f"         Errores: {[e.split(':')[0] for e in envelope.errors]}")
                
                # Auto-corrección
                correction_prompt = (
                    f"[CORRECCIÓN PVC-U]\n"
                    f"Tu resultado falló la validación continua.\n\n"
                    f"Errores:\n" + "\n".join(f"- {e}" for e in envelope.errors) + "\n\n"
                    f"Por favor corrige estos problemas."
                )
                
                corrected_result = self._run_agent(subtask["role"], correction_prompt)
                results[subtask["role"]] = corrected_result
            else:
                print(f"[PVC-U] ✅ Validado correctamente")
                results[subtask["role"]] = agent_result
        
        return results
    
    def _run_agent(self, agent_name: str, prompt: str) -> str:
        """Simula ejecución de agente (en producción sería subprocess real)."""
        # En producción real:
        # cmd = ["mimo", "run", "--dangerously-skip-permissions", prompt]
        # result = subprocess.run(cmd, capture_output=True, text=True)
        # return result.stdout + result.stderr
        
        return f"[Simulación] {agent_name} procesó: {prompt[:100]}..."


async def main():
    """Demo de integración CEO + PVC-U."""
    ceo = AgencyCEO()
    
    # Ejemplo realista: construir SaaS completo
    task = "Construir sistema de gestión de proyectos con Next.js y PostgreSQL"
    
    results = await ceo.execute_task(task, Domain.WEB_DESIGN)
    
    print("\n[CEO] Resultados finales:")
    for role, content in results.items():
        print(f"  {role}: {content[:80]}...")


if __name__ == "__main__":
    asyncio.run(main())
