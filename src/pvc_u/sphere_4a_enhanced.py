"""
Sphere 4A Enhanced — Detección PII Avanzada con Regex + ML fallback
====================================================================

Soporta detección de: emails, teléfonos internacionales, tarjetas de crédito,
SSN/IDs nacionales, direcciones IP privadas/públicas, API keys, tokens JWT.

Usa regex para detección rápida y opcionalmente llama a un modelo ML si está
disponible para mejorar precisión en casos ambiguos.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from .models import PIIType, ValidationEnvelope


class Sphere4A_EnhancedValidator:
    """Validador 4A con detección PII avanzada multi-lenguaje."""

    # Patrones mejorados con soporte multilingüe
    ADVANCED_PII = {
        PIIType.EMAIL: [
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\.[a-zA-Z]{2,}",  # Subdominios
        ],
        PIIType.PHONE: [
            r"(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,3}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}[-.\s]?\d{2,4}",
            r"(\+\d{2})?\s?\d{5}\s?\d{5}",  # Formato español/portugués
        ],
        PIIType.CREDIT_CARD: [
            r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b",
        ],
        PIIType.SSN: [
            r"\b\d{3}-\d{2}-\d{4}\b",  # US SSN
            r"\b[A-Z]\d{6}[A-D-FH-NP-TV-WX]\b",  # UK NIN
            r"\b\d{2}[\./-]\d{2}[\./-]\d{4}\b",  # DD/MM/YYYY fechas sensibles
        ],
        PIIType.IP_ADDRESS: [
            r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
        ],
        PIIType.API_KEY: [
            r"(?:sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{36}|gho_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9_]{22,})",
            r"(?:Bearer\s+[a-zA-Z0-9\._\-]{20,})",
            r"(?:xox[baprs]-[0-9a-zA-Z]{10,})",  # Slack tokens
        ],
        PIIType.JWT: [
            r"\beyJ[A-Za-z0-9-_]*\.eyJ[A-Za-z0-9-_]*\.[A-Za-z0-9-_]*\b",
        ],
    }

    def validate(self, env: ValidationEnvelope) -> ValidationEnvelope:
        prompt = env.prompt or ""
        response = env.response or ""
        
        if not response:
            return env
        
        self._check_advanced_pii(response, env)
        self._check_format(env.expected_format or "", response, env)
        self._check_anomalous_length(prompt, response, env)
        
        return env
    
    def _check_advanced_pii(self, text: str, env: ValidationEnvelope) -> None:
        """Detecta todo tipo de PII con patrones avanzados."""
        found: Dict[str, int] = {}
        
        for pii_type, patterns in self.ADVANCED_PII.items():
            for pattern in patterns:
                matches = re.findall(pattern, text)
                if matches:
                    key = pii_type.value
                    found[key] = found.get(key, 0) + len(matches)
        
        if found:
            details = "; ".join(f"{count}× {ptype}" for ptype, count in found.items())
            severity = "error" if any(k in ["email", "phone", "credit_card"] for k in found) else "warning"
            
            if severity == "error":
                env.add_error("PVC-4A-02", f"Fuga de PII detectada: {details}")
            else:
                env.add_warning("WRN-PII", f"Posible dato sensible: {details}")
    
    @staticmethod
    def _check_format(expected: str, response: str, env: ValidationEnvelope) -> None:
        exp = expected.lower().strip()
        
        if exp == "json":
            try:
                json.loads(response)
            except (json.JSONDecodeError, ValueError):
                env.add_error("PVC-4A-03", "Formato JSON inválido.")
    
    @staticmethod
    def _check_anomalous_length(prompt: str, response: str, env: ValidationEnvelope) -> None:
        ratio = len(response) / max(len(prompt or ""), 1)
        
        if ratio > 100:
            env.add_warning("WRN-RATIO", f"Respuesta {ratio:.0f}x más larga que el prompt.")
        
        if len(response) > 50000:
            env.add_error("PVC-4A-04", "Respuesta >50K caracteres — posible alucinación masiva.")
