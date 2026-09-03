# PVC-U — Protocolo de Validación Continua Universal

**Kernel de gobernanza para Empresas de IA Autónomas de Nivel Empresarial**

Garantiza que la IA no alucina, no filtra datos y cumple normativa regulatoria (HIPAA, PCI-DSS, GDPR).

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
# Desde PyPI (cuando disponible)
pip install pvc-u

# Localmente desde repo
cd pvc-u-core
pip install -e .[postgres]

# Con Docker
docker-compose up -d
```

## Uso Rápido

### Python API

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
    for error in result.errors:
        print(f"ERR: {error}")
    
    # Auto-correction automática está activada por defecto
```

### CLI

```bash
# Inicializar configuración
pvcu init --db-url postgresql://... --llm-base-url http://localhost:4000/v1

# Validar prompt/response
pvcu validate salud \
  -p "¿Cuál es el tratamiento?" \
  -r "El paciente debe tomar..."

# Generar reporte completo
pvcu report --domain salud

# Auto-heal tarea completa
pvcu heal "Generar informe médico HIPAA-compliant" \
  -c '{"patient_id": "X", "date": "2026-09-03"}'
```

### FastAPI Integration

```python
# En tu ceo.py o app principal:
from pvc_u import PVCUOrchestrator, Domain

pvc = PVCUOrchestrator(db_url="postgresql://...")

async def exec_design(state):
    prompt = "Crear landing page con GSAP"
    
    # Validar antes de entregar al cliente
    envelope = await pvc.validate(
        domain="web_design",
        payload={"prompt": prompt, "response": agent_result}
    )
    
    if not envelope.is_valid:
        correction = f"Corrige estos errores: {envelope.errors}"
        agent_result = run_opencodex(correction)
        
    state["results"]["design"] = agent_result
    return state
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

## Variables de Entorno

```bash
PVC_U_DB_URL=sqlite+pysqlite:///./pvc_u_ledger.db
PVC_U_LLAM_BASE_URL=http://localhost:4000/v1
PVC_U_LL_API_KEY=not-needed
PVC_U_AUTO_CORRECTION=true
PVC_U_RETRY_MAX_ATTEMPTS=2
```

## Stack Técnico

- **Python 3.10+** con type hints completos
- **Pydantic v2** para models validados
- **SQLAlchemy 2.0** para abstracción DB (SQLite/Postgres)
- **LiteLLM** para auditoría semántica vía LLM
- **FastAPI** para API REST (opcional)
- **Rich** para CLI formatting

## Plan de Negocio con PVC-U

### Producto "Agencia Cero-Alucinación" ($10,000/mes)
Vendes a bancos y hospitales el kernel autónomo completo garantizando que ninguna decisión IA pasa sin PVCU. El Ledger se convierte en venta clave: ofreces auditoría inmutable 24/7.

### Servicio Cumplimiento HIPAA/PCI-DSS ($50,000 setup)
Creas adaptadores de dominio específicos para cada sector regulado. Un hospital paga $50k por el deploy de validadores FHIR + agentes de historiales clínicos sin filtrar PII.

### Licencia Protocolo SaaS
Empaquetas PVCU como microservicio FastAPI y vendés a otras agencias que usan Cursor/Claude pero no tienen infraestructura de validación.

## Roadmap V2

- [ ] MCP server integration
- [ ] OPA/Gatekeeper policies
- [ ] Kubernetes Gatekeeper adapter
- [ ] CloudEvents format support
- [ ] Webhook alerts on failure threshold

## License

MIT — Usa libremente en producción empresarial.
