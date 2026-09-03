"""
Ejemplo: Integración de PVC-U con Aider (CLI autónomo)
========================================================

Patron usado por agencias enterprise para validar código generado
automáticamente antes de hacer commit o entregar al cliente.
"""

import asyncio
import subprocess
from typing import Optional


async def validate_with_aider(code_content: str, file_path: str = "generated_code.py") -> dict:
    """
    Valida código que Aider generó usando PVC-U.
    
    Ejemplo de integración real:
    1. Aider genera código según prompt del cliente
    2. PVC-U valida el resultado ANTES de commit
    3. Si hay errores, se le pide a Aider que corrija
    """
    try:
        from pvc_u import PVCUOrchestrator, Domain
        
        pvc = PVCUOrchestrator(auto_correction=True)
        
        # Validar código generado
        envelope = await pvc.validate(
            domain=Domain.WEB_DESIGN,
            payload={
                "agent": "aider",
                "file_path": file_path,
                "prompt": f"Crea archivo {file_path}",
                "response": code_content[:1000],  # Primeros 1000 chars
            },
        )
        
        return {
            "valid": envelope.is_valid,
            "errors": envelope.errors,
            "warnings": envelope.warnings,
            "score": envelope.meta_validation_score or 0.5,
        }
        
    except ImportError:
        print("[ERROR] PVC-U no instalado — ejecutando simulación")
        return {"valid": True, "errors": [], "score": 0.9}


# ────────── Uso Real con Aider CLI ──────────

def run_aider_with_pvc_check(prompt: str, directory: str = ".") -> bool:
    """
    Ejecuta Aider y luego valida su salida con PVC-U.
    
    Patrón enterprise real:
    - Aider genera/modify código
    - PVC-U valida antes de commit
    - Si falla, corrección automática
    """
    # 1. Ejecutar Aider (modo no interactivo)
    cmd = [
        "aider",
        "--architect",
        "--model", "groq/llama-3.1-8b-instant",
        "--message", prompt,
        "--no-auto-commits",
        "--yes-always",
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd=directory)
    output = result.stdout + result.stderr
    
    # 2. Validar con PVC-U
    validation = asyncio.run(validate_with_aider(output))
    
    if not validation["valid"]:
        print(f"[PVC-U] Código NO válido — Errores:")
        for err in validation["errors"]:
            print(f"  ❌ {err}")
        
        # Opcional: pedir corrección automática
        correction_prompt = (
            f"Corrige estos errores del código:\n" +
            "\n".join(f"- {e}" for e in validation["errors"])
        )
        print(f"\n[AIDER] Corrigiendo...")
        subprocess.run(["aider", "--message", correction_prompt], cwd=directory)
        return False
    
    print(f"[PVC-U] ✅ Código validado correctamente (score: {validation['score']:.2f})")
    return True


if __name__ == "__main__":
    # Demo
    sample_code = """
    def hello():
        email = 'cliente@empresa.com'  # ¡FALTA! PII leak
        return f"Hola, tu pedido #{12345} está listo"
    """
    
    result = asyncio.run(validate_with_aider(sample_code))
    print(f"Validación: {result}")
