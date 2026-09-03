"""
PVC-U CLI — Interfaz de línea de comandos
===========================================

Comandos disponibles:
  pvcu init        Crear configuración por defecto
  pvcu validate    Validar prompt/response desde terminal
  pvcu report      Generar reporte del ledger
  pvcu stats       Estadísticas globales
  pvcu heal        Auto-heal task con validación iterativa
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .models import Domain, PVCUConfig
from .orchestrator import PVCUOrchestrator


console = Console()


@click.group()
def main():
    """PVC-U — Protocolo de Validación Continua Universal"""
    pass


@main.command()
@click.option("--db-url", default=None, help="URL de base de datos")
@click.option("--llm-base-url", default=None, help="Base URL del proxy LiteLLM")
@click.option("--llm-api-key", default=None, help="API key para LLMs auxiliares")
def init(db_url, llm_base_url, llm_api_key):
    """Inicializar configuración PVC-U."""
    config = PVCUConfig(
        db_url=db_url or "sqlite+pysqlite:///./pvc_u_ledger.db",
        llm_api_base=llm_base_url or "http://localhost:4000/v1",
        llm_api_key=llm_api_key or "not-needed",
    )
    path = config.save()
    console.print(f"[green]✓[/] Configuración guardada en: {path}")
    console.print(config.model_dump_json(indent=2))


@main.command()
@click.argument("domain", required=False, default="general")
@click.option("--prompt", "-p", help="Prompt a validar")
@click.option("--response", "-r", help="Response del agente IA")
@click.option("--output", "-o", type=click.Path(), help="Guardar resultado en archivo JSON")
def validate(domain, prompt, response, output):
    """Validar un prompt y respuesta contra las esferas PVC-U."""
    from .models import ValidationEnvelope

    env = ValidationEnvelope(
        domain=Domain(domain),
        payload={"prompt": prompt or "", "response": response or ""},
        profile="default",
    )

    async def run_validation():
        pvc = PVCUOrchestrator()
        # Ejecutar esferas manualmente para CLI
        pvc.sphere_3a.validate(env)
        pvc.sphere_4a.validate(env)
        if prompt and response:
            pvc.sphere_2a.validate(env)
        return env

    result = asyncio.run(run_validation())

    # Output formatting
    table = Table(title=f"Resultados Validación - {domain.upper()}")
    table.add_column("Tipo", style="cyan")
    table.add_column("Código", style="yellow")
    table.add_column("Detalle", style="white")

    for error in result.errors:
        code = error.split(":")[0] if ":" in error else "ERR"
        table.add_row("[red]ERROR[/]", code, error)

    for warning in result.warnings:
        code = warning.split(":")[0] if ":" in warning else "WRN"
        table.add_row("[yellow]WARN[/]", code, warning)

    console.print(table)

    status_color = "green" if result.is_valid else "red"
    score = result.meta_validation_score or 0.5
    console.print(
        f"\n[bold {status_color}]Estado:[/] {'VALIDADO' if result.is_valid else 'FALLÓ'} | "
        f"Score: {score:.2f} | Errores: {len(result.errors)} | Warnings: {len(result.warnings)}"
    )

    if output:
        with open(output, "w") as f:
            json.dump(result.to_dict(), f, indent=2)
        console.print(f"\n[yellow]Resultado guardado en:[/]{output}")


@main.command()
@click.option("--domain", default=None, help="Filtrar por dominio")
@click.option("--json-output", is_flag=True, help="Output JSON puro")
def report(domain, json_output):
    """Generar reporte del estado de validación."""
    pvc = PVCUOrchestrator()

    async def run_report():
        return await pvc.generate_report(Domain(domain) if domain else None)

    data = asyncio.run(run_report())

    if json_output:
        print(json.dumps(data, indent=2))
        return

    console.print("\n[bold]📊 Reporte PVC-U[/]")
    console.print(f"Total entradas:     [cyan]{data.get('total_entries', 0)}[/]")
    console.print(f"Tasa validación:    [green]{data.get('validation_rate', 0)}%[/]")
    console.print(f"Score promedio:     [blue]{data.get('avg_meta_score', 0):.3f}[/]")


@main.command()
@click.argument("task")
@click.option("--context-json", "-c", help="Contexto adicional como JSON string")
def heal(task, context_json):
    """Auto-heal: validar → detectar fallo → corregir con LLM → revalidar."""
    ctx = {}
    if context_json:
        try:
            ctx = json.loads(context_json)
        except json.JSONDecodeError:
            console.print("[red]JSON inválido para contexto[/]")
            sys.exit(1)

    pvc = PVCUOrchestrator(auto_correction=True, retry_max_attempts=3)

    async def run_heal():
        return await pvc.auto_heal(task=task, context=ctx)

    result = asyncio.run(run_heal())

    status = result["status"]
    status_icon = "✅" if status == "healed" else "❌"
    iterations = result["iterations"]

    console.print(Panel(
        f"[bold]{status_icon} STATUS:[/] {status.upper()}\n"
        f"Iteraciones: {iterations}\n"
        f"Auto-corregido: {result['auto_corrected']}",
        title="Auto-Heal Result",
        border_style="green" if status == "healed" else "red",
    ))

    # Show final errors if any
    if not result["auto_corrected"]:
        final_result = result["final_result"]
        if final_result.get("errors"):
            console.print("\n[red]Errores finales:[/]")
            for err in final_result["errors"]:
                console.print(f"  - {err}")


if __name__ == "__main__":
    main()
