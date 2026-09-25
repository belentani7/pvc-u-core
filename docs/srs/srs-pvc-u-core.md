# SRS -- pvc-u-core
Fecha: 2026-09-25 | Estado: Draft | Traza a: PRD prd-pvc-u-core.md

## Requisitos funcionales

| ID | Requisito | Traza PRD | Prioridad |
|---|---|---|---|
| FR-001 | El sistema implementa: Python 3.10+ con type hints completos | F1 | Must |
| FR-002 | El sistema implementa: Pydantic v2 para models validados | F2 | Must |
| FR-003 | El sistema implementa: SQLAlchemy 2.0 para abstracción DB (SQLite/Postgres) | F3 | Must |
| FR-004 | El sistema implementa: LiteLLM para auditoría semántica vía LLM | F4 | Must |
| FR-005 | El sistema implementa: FastAPI para API REST (opcional) | F5 | Must |
| FR-006 | El sistema implementa: Rich para CLI formatting | F6 | Must |
| FR-007 | El sistema implementa: [ ] MCP server integration | F7 | Must |
| FR-008 | El sistema implementa: [ ] OPA/Gatekeeper policies | F8 | Must |

## Requisitos no funcionales

| ID | Requisito | Metrica | Traza |
|---|---|---|---|
| NFR-001 | Build reproducible | `build` pasa en CI | todos |
| NFR-002 | Calidad estatica | lint + typecheck sin errores | todos |
| NFR-003 | Seguridad | 0 secretos; validacion de entrada | FR-001 |
| NFR-004 | Observabilidad | logs estructurados y errores claros | todos |
| NFR-005 | Accesibilidad (si hay UI) | WCAG 2.1 AA | FR-001 |
| NFR-006 | CI verde | workflow en cada PR | todos |

## Trazabilidad

`PRD -> FR/NFR -> tests -> verificacion`. Todo cambio actualiza la documentacion
en el mismo PR y debe pasar la suite antes de fusionar.
