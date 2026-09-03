"""
Metrics — Monitoreo Prometheus para PVC-U
==========================================

Expone métricas en /metrics para integración con Grafana/Prometheus:
- validation_requests_total
- validation_errors_total
- validation_duration_seconds
- pvc_validation_by_domain
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CollectorRegistry

# Contadores principales
VALIDATION_REQUESTS = Counter(
    "validation_requests_total",
    "Total de validaciones realizadas",
    ["domain", "status"],
)

VALIDATION_ERRORS = Counter(
    "validation_errors_total",
    "Errores detectados por esfera",
    ["sphere", "error_type"],
)

VALIDATION_DURATION = Histogram(
    "validation_duration_seconds",
    "Tiempo de validación en segundos",
    ["domain"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
)

# Gauges actuales
ACTIVE_VALIDATIONS = Gauge(
    "active_validations",
    "Validaciones en progreso ahora",
)

DOMAIN_ERROR_RATE = Gauge(
    "domain_error_rate_percent",
    "Tasa de error por dominio (%)",
    ["domain"],
)


def record_validation(domain: str, status: str, duration: float) -> None:
    """Registra una validación completada."""
    VALIDATION_REQUESTS.labels(domain=domain, status=status).inc()
    VALIDATION_DURATION.labels(domain=domain).observe(duration)
    
    # Actualizar error rate si hubo errores
    if status == "invalid":
        DOMAIN_ERROR_RATE.labels(domain=domain).inc()


def get_metrics() -> bytes:
    """Devuelve métricas formateadas para Prometheus scrape."""
    registry = CollectorRegistry()
    VALIDATION_REQUESTS.register(registry)
    VALIDATION_ERRORS.register(registry)
    VALIDATION_DURATION.register(registry)
    ACTIVE_VALIDATIONS.register(registry)
    DOMAIN_ERROR_RATE.register(registry)
    return generate_latest(registry)
