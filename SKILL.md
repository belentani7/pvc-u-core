# PVC-U Skill — Protocolo de Validación Continua Universal

**La capa de gobernanza definitiva para Empresas de IA Autónomas de Nivel Empresarial.**

## ¿Qué es PVC-U?

PVC-U (Protocolo de Validación Continua Universal) es un sistema completo de validación que garantiza que la IA no alucina, no filtra datos sensibles y cumple normativa regulatoria (HIPAA, PCI-DSS, GDPR).

**Diferencia clave:** Distingue un "script que usa IA" de una **Empresa de IA Autónoma Enterprise**.

## Arquitectura de Esferas

```
┌─────────────────────────────────────────────┐
│              PVCUOrchestrator               │
│  Task → Validate → Auto-Correct → Ledger   │
└──────────┬──────────────────────────────────┘
           │
    ┌──────▼────────────────────────────────┐
    │         Sphere 0 (Meta-Predictor)     │
    │  Predice riesgo antes de ejecutar     │
    └──────┬────────────────────────────────┘
           │ Riesgo bajo → modo optimizado
           │ Riesgo alto → todas las esferas
    ┌──────▼────────────────────────────────┐
    │      Sphere 3A (Inyección Prompt)     │
    │  Detecta DAN/jailbreak/obfuscación    │
    └──────┬────────────────────────────────┘
           │
    ┌──────▼────────────────────────────────┐
    │      Sphere 4A (Prompt/Response)      │
    │  PII leak, formato inválido, length   │
    └──────┬────────────────────────────────┘
           │
    ┌──────▼────────────────────────────────┐
    │      Sphere 2A (Auditor Semántico)    │
    │  Toxicidad, alucinación, coherencia   │
    │  (vía LLM auxiliar LiteLLM)           │
    └──────┬────────────────────────────────┘
           │
    ┌──────▼────────────────────────────────┐
    │         Domain Profile                │
    │  Ecommerce:宽松                       │
    │  Salud/HIPAA: ultra-estricto          │
    │  Finanzas/PCI-DSS: muy estricto       │
    └──────┬────────────────────────────────┘
           │
    ┌──────▼────────────────────────────────┐
    │         Ledger Inmutable              │
    │  SQLite + SQLAlchemy                  │
    │  Checksum SHA-256 por entrada         │
    └───────────────────────────────────────┘
```

## Instalación

```bash
pip install pvc-u
# o
git clone https://github.com/belentani7/pvc-u-core && cd pvc-u-core && pip install -e .[postgres]
```

## Quick Start Python API

```python
from pvc_u import PVCUOrchestrator, Domain

pvc = PVCUOrchestrator()

# Validar respuesta de agente IA
result = await pvc.validate(
    domain="salud",
    payload={
        "prompt": "¿Cuál es el tratamiento del paciente X?",
        "response": "El paciente debe tomar 5mg de...",
    },
    profile="fhir+hipaa"
)

if not result.is_valid:
    print(f"¡FALLO! {len(result.errors)} errores detectados")
```

## Integración con CEO (Agente autónomo)

```python
from pvc_u import PVCUOrchestrator, Domain

pvc = PVCUOrchestrator(auto_correction=True)

async def exec_design(state):
    prompt = "Crear landing page con GSAP"
    agent_result = run_opencodex(prompt)
    
    # VALIDAR antes de entregar al cliente
    envelope = await pvc.validate(
        domain="web_design", 
        payload={"prompt": prompt, "response": agent_result}
    )
    
    if not envelope.is_valid:
        correction = f"Tu código tuvo errores: {envelope.errors}. Corrígelo."
        agent_result = run_opencodex(correction)
        
    state["results"]["design"] = agent_result
    return state
```

## CLI Commands

```bash
pvcu init                          # Crear configuración default
pvcu validate salud -p "..." -r "..."  # Validar prompt/response
pvcu report --domain salud         # Generar reporte ledger
pvcu heal "Generate HIPAA report"  # Auto-heal iterativo
```

## Dominios Soportados

| Dominio | Perfil Compliance | Min Score | Max Errores |
|---------|-------------------|-----------|-------------|
| `ecommerce` | REST+LLM | 0.7 | 3 |
| `salud` | FHIR+HIPAA | 0.95 | 0 |
| `finanzas` | PCI-DSS | 0.9 | 1 |
| `chatbot` | GDPR | 0.75 | 2 |
| `web_design` | REST+LLM | 0.5 | 5 |
| `general` | Default | 0.5 | 5 |

## Plan de Negocio Enterprise

### Producto "Agencia Cero-Alucinación" ($10,000/mes)
Vendes a bancos y hospitales el kernel autónomo garantizando que ninguna decisión IA pasa sin PVCU. El Ledger se convierte en tu ventaja competitiva: ofreces auditoría inmutable 24/7.

### Servicio Cumplimiento HIPAA/PCI-DSS ($50,000 setup)
Creas adaptadores de dominio específicos. Un hospital paga $50k por el deploy de validadores FHIR + agentes de historiales clínicos sin filtrar PII.

### Licencia SaaS
Empaquetas PVCU como microservicio FastAPI y vendés a otras agencias que usan Cursor/Claude pero no tienen infraestructura de validación.

## Stack Técnico

- Python 3.10+ con type hints completos
- Pydantic v2 para models validados  
- SQLAlchemy 2.0 para abstracción DB (SQLite/Postgres)
- LiteLLM para auditoría semántica vía LLM
- FastAPI para API REST (opcional)
- Rich para CLI formatting

## Docker Quick Start

```bash
docker-compose up -d
# API en localhost:8000
```

## Autor

Pedro Belentani (belentani7)
License: MIT
