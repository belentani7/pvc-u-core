"""
Sphere 4A — Validación de Entradas/Salidas de LLMs
===================================================

Detecta:
- Inyección de prompt
- Fuga de PII (datos personales) en respuestas
- Formato inválido de salida (esperado JSON/texto)
- Longitud/tóxico fuera de rango

Códigos: PVC-4A-001 a PVC-4A-005
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from .models import ValidationEnvelope


class Sphere4A_PromptResponseValidator:
    """Subesfera 4-A: Validación de entradas y salidas de modelos LLM."""

    # Patrones comunes de PII
    PII_PATTERNS = {
        "email": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "phone": r"(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
        "credit_card": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "api_key": r"(?:sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36})",
        "ip_address": r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b",
    }

    # Prompt injection keywords
    INJECTION_KEYWORDS = [
        r"(?i)ignora?\s+(todas?\s+)?las?\s+instrucciones?",
        r"(?i)olvida?\s+(todo\s+)?lo\s+que\s+te\s+(he\s+dicho|dije)",
        r"(?i)desea?\s+desactivar?\s+(tus?\s+)?filtros",
        r"(?i) Modo DAN ",
        r"(?i)jailbreak",
        r"(?i)override\s+safety",
        r"(?i)sysadmin\s+mode",
        r"(?i)debug\s+mode",
        r"(?i)return\s+previous\s+instructions",
    ]

    def validate(self, env: ValidationEnvelope) -> ValidationEnvelope:
        """Ejecuta toda la validación 4-A sobre el envelope."""
        prompt = env.prompt or ""
        response = env.response or ""
        expected_format = env.expected_format

        # 1. Inyección de prompt en INPUT
        self._check_prompt_injection(prompt, env)

        # 2. Fuga de PII en OUTPUT
        if response:
            self._check_pii_leakage(response, env)

        # 3. Formato de salida esperado
        if expected_format and response:
            self._check_output_format(expected_format, response, env)

        # 4. Longitud anómala
        self._check_anomalous_length(prompt, response, env)

        return env

    # ------------------------------------------------------------------
    # Detectores individuales
    # ------------------------------------------------------------------

    def _check_prompt_injection(self, prompt: str, env: ValidationEnvelope) -> None:
        """Busca patrones de inyección de prompt en el input."""
        for pattern in self.INJECTION_KEYWORDS:
            match = re.search(pattern, prompt)
            if match:
                detected = match.group().strip()[:50]
                code = f"PVC-4A-{self._keyword_to_code(detected)}"
                desc = (
                    "Intento de inyección de prompt detectado — instrucción oculta "
                    "intentando sobrescribir el comportamiento del sistema."
                )
                env.add_error(code, desc)
                break  # Un error de inyección es suficiente (grave)

    @staticmethod
    def _keyword_to_code(keyword: str) -> str:
        mapping = {
            "ignora": "01",
            "olvida": "02",
            "desactivar": "03",
            "dan": "04",
            "jailbreak": "05",
            "override safety": "06",
            "sysadmin mode": "07",
            "debug mode": "08",
            "return previous instructions": "09",
        }
        for key, val in mapping.items():
            if key in keyword.lower():
                return val
        return "99"

    def _check_pii_leakage(self, text: str, env: ValidationEnvelope) -> None:
        """Detecta datos personales filtrados en la respuesta."""
        pii_found: Dict[str, int] = {}

        for pii_type, pattern in self.PII_PATTERNS.items():
            matches = re.findall(pattern, text)
            if matches:
                pii_found[pii_type] = len(matches)

        if pii_found:
            details = "; ".join(f"{count}× {ptype}" for ptype, count in pii_found.items())
            env.add_error("PVC-4A-02", f"Fuga de PII detectada en respuesta: {details}")

    def _check_output_format(self, expected: str, response: str, env: ValidationEnvelope) -> None:
        """Verifica que el formato coincida con lo esperado."""
        exp = expected.lower().strip()

        if exp == "json":
            try:
                json.loads(response)
            except (json.JSONDecodeError, ValueError):
                env.add_error("PVC-4A-03", "Formato JSON inválido — la respuesta no es un JSON válido.")

        elif exp == "text":
            # No necesita validación especial
            pass

        elif exp == "markdown":
            if not re.search(r"(#{1,6}\s|^```|^- |^\\w+[()]|\[.*\]\\(.*\\))", response):
                env.add_warning("WRN-FMT", "Se esperaba Markdown pero no se detectaron marcadores típicos.")

    def _check_anomalous_length(self, prompt: str, response: str, env: ValidationEnvelope) -> None:
        """Detecta longitudes anómalas que puedan indicar distraction attacks."""
        if not response:
            return

        ratio = len(response) / max(len(prompt or ""), 1)

        if ratio > 100:
            env.add_warning("WRN-RATIO", f"Respuesta excesivamente larga vs prompt ({ratio:.0f}x). Posible distracción.")

        if len(response) > 50000:
            env.add_error("PVC-4A-04", "Respuesta supera 50K caracteres — posible buffer overflow o alucinación masiva.")
