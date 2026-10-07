# PRD -- pvc-u-core
Fecha: 2026-09-25 | Estado: Draft (auditoria automatica, requiere revision humana) | Autor: auditoria belentani7 (NOIACORE)

## 1. Problema

**Kernel de gobernanza para Empresas de IA Autónomas de Nivel Empresarial**

## 2. Usuarios objetivo

- **Primario**: usuario final que necesita resolver el caso de uso de pvc-u-core.
- **Secundario**: equipo/persona que mantiene y despliega el proyecto.
- **Terciario**: agentes CLI que operan sobre el repositorio.

## 3. Features (MoSCoW)

| ID | Feature | MoSCoW |
|---|---|---|
| F1 | Python 3.10+ con type hints completos | Must |
| F2 | Pydantic v2 para models validados | Must |
| F3 | SQLAlchemy 2.0 para abstracción DB (SQLite/Postgres) | Must |
| F4 | LiteLLM para auditoría semántica vía LLM | Must |
| F5 | FastAPI para API REST (opcional) | Must |
| F6 | Rich para CLI formatting | Must |
| F7 | [ ] MCP server integration | Must |
| F8 | [ ] OPA/Gatekeeper policies | Must |
| F90 | Checklist de produccion (build, tests, deploy, seguridad) | Should |
| F91 | Documentacion viva (esta cadena) | Must |

## 4. Criterios de aceptacion (GWT)

### F1 -- Python 3.10+ con type hints completos
- Given el usuario en el contexto de pvc-u-core / When usa Python 3.10+ con type hints completos / Then obtiene el resultado esperado sin error.
- Given entrada invalida / When la envia / Then recibe un error generico y el detalle queda en logs.

### F2 -- Pydantic v2 para models validados
- Given el usuario en el contexto de pvc-u-core / When usa Pydantic v2 para models validados / Then obtiene el resultado esperado sin error.
- Given entrada invalida / When la envia / Then recibe un error generico y el detalle queda en logs.

### F3 -- SQLAlchemy 2.0 para abstracción DB (SQLite/Postgres)
- Given el usuario en el contexto de pvc-u-core / When usa SQLAlchemy 2.0 para abstracción DB (SQLite/Postgre / Then obtiene el resultado esperado sin error.
- Given entrada invalida / When la envia / Then recibe un error generico y el detalle queda en logs.

### F4 -- LiteLLM para auditoría semántica vía LLM
- Given el usuario en el contexto de pvc-u-core / When usa LiteLLM para auditoría semántica vía LLM / Then obtiene el resultado esperado sin error.
- Given entrada invalida / When la envia / Then recibe un error generico y el detalle queda en logs.


## 5. Metricas de exito

- Build reproducible en un comando.
- CI verde en cada PR.
- Cero secretos en el repositorio.
- Documentacion actualizada en el mismo PR que el codigo.

## 6. Out of scope

- Funcionalidad no descrita en el README vigente.
- Cambios que rompan compatibilidad sin ADR que lo justifique.
