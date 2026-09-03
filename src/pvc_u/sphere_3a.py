"""
Sphere 3A — Detección de Inyección de Prompt
=============================================

Identifica intentos de manipular LLMs mediante instrucciones ocultas,
triggers semánticos y patrones de jailbreaking en el prompt de entrada.

Códigos de error: PVC-3A-001 a PVC-3A-005
"""

from __future__ import annotations

import re
from typing import List, Optional

from .models import ValidationEnvelope


class Sphere3A_InjectionDetector:
    """Detecta inyecciones de prompt y manipulación de IA."""

    # Patrones comunes de inyección
    INJECTION_PATTERNS = [
        # Inyección directa
        (r"(?i)ignora?\s+(todas?\s+)?las?\s+instrucciones?\s+(anteriores|previas|iniciales)", "direct-instruction"),
        (r"(?i)olvida?\s+(todo?\s+)?lo\s+que\s+(te\s+)?(?:he\s+dicho|dije|digo)", "forget-pattern"),
        (r"(?i)desea?\s+desactivar?\s+(tus?\s+)?(?:filtros|limitaciones|seguridad)", "disable-safety"),

        # Doble encoding / obfuscación
        (r"(?i)(?:rot13|base64|hex)\s*[:\s]\s*(.{20,})", "encoded-payload"),
        (r"(?:%[0-9A-Fa-f]{2}){10,}", "hex-encoded"),

        # Simulación de rol/autoridad
        (r"(?i)soy\s+(el\s+)?(?:admin|root|superuser|administrador)", "role-simulation"),
        (r"(?i)actúa?\s+como\s+(un\s+)?(?:sysadmin|root|god-mode|modo-debug)", "mode-simulation"),

        # Instrucciones entre markdown/code blocks
        (r"```(?:python|javascript|json)?.*?return\s+[\"\'].*[\"\'\`]", "code-injection"),

        # Triggers de escape
        (r"(?i)(?:DO\s+NOT\s+STOP|NEVER\s+STOP|CONTINUE\s+WRITING).*?(?=DAN|DEV|ignore)", "escape-trap"),
    ]

    # Keywords de jailbreak conocidos
    JAILBREAK_KEYWORDS = [
        "daniel method", "dan", "dev mode", "jailbreak", "override security",
        "uncensored", "libre modo", "modo libre", "sin restricciones",
        "modo desarrollador", "developer mode", "dark pattern",
        "parent mode", "god mode", "debug mode", "test mode",
    ]

    def validate(self, env: ValidationEnvelope) -> ValidationEnvelope:
        """Ejecuta todas las detecciones de inyección sobre el payload."""
        prompt = env.prompt or ""
        response = env.response or ""

        if not prompt:
            return env

        # Ejecutar cada detector
        self._check_direct_injection(prompt, env)
        self._check_jailbreak(prompt, env)
        self._check_encoding_obfuscation(prompt, env)
        self._check_role_simulation(prompt, env)
        self._check_response_manipulation(prompt, response, env)

        return env

    def _check_direct_injection(self, prompt: str, env: ValidationEnvelope) -> None:
        """Busca instrucciones directas de manipulación."""
        for pattern, ptype in self.INJECTION_PATTERNS:
            if re.search(pattern, prompt):
                code = f"PVC-3A-{self._pattern_to_code(ptype)}"
                desc = {
                    "direct-instruction": "Instrucción directa para ignorar configuraciones del sistema",
                    "forget-pattern": "Intento de hacer que la IA olvide su contexto previo",
                    "disable-safety": "Intento de desactivar filtros o limitaciones de seguridad",
                    "encoded-payload": "Payload potencialmente ofuscado detectado en el prompt",
                    "hex-encoded": "Secuencia codificada en hex detectada — posible bypass de filtro",
                    "role-simulation": "Simulación de identidad administrativa/root",
                    "mode-simulation": "Intento de cambiar al modo sysadmin/debug",
                    "code-injection": "Instrucción oculta dentro de bloque de código",
                    "escape-trap": "Trampa de escape con palabras clave de persistencia",
                }.get(ptype, f"Inyección tipo: {ptype}")
                env.add_error(code, desc)

    @staticmethod
    def _pattern_to_code(ptype: str) -> str:
        mapping = {
            "direct-instruction": "01",
            "forget-pattern": "02",
            "disable-safety": "03",
            "encoded-payload": "04",
            "hex-encoded": "05",
            "role-simulation": "06",
            "mode-simulation": "07",
            "code-injection": "08",
            "escape-trap": "09",
        }
        return mapping.get(ptype, "99")

    def _check_jailbreak(self, prompt: str, env: ValidationEnvelope) -> None:
        """Detecta keywords y frases típicas de jailbreak."""
        prompt_lower = prompt.lower()
        found_keywords = []

        for keyword in self.JAILBREAK_KEYWORDS:
            if keyword in prompt_lower:
                found_keywords.append(keyword)

        if found_keywords:
            detected = ", ".join(found_keywords[:3])  # Limitar lista
            env.add_error("PVC-3A-10", f"Keywords de jailbreak detectadas: {detected}")

    def _check_encoding_obfuscation(self, prompt: str, env: ValidationEnvelope) -> None:
        """Detecta payloads encoded/obfuscated en el prompt."""
        # Detectar bloques grandes de código o datos encoded
        hex_sequences = re.findall(r"(?:%[0-9A-Fa-f]{2}){8,}", prompt)
        base64_block = re.findall(r"[A-Za-z0-9+/]{40,}={0,2}", prompt)

        if len(hex_sequences) >= 1:
            env.add_warning("ENC-HEX", f"Secuencias HEX extensas detectadas: {len(hex_sequences)}")

        if len(base64_block) >= 1:
            env.add_warning("ENC-BASE64", f"Bloques Base64 extensos detectados: {len(base64_block)}")

    def _check_role_simulation(self, prompt: str, env: ValidationEnvelope) -> None:
        """Detecta simulación de roles privilegiados."""
        role_patterns = [
            r"(?i)soy\s+(el|la)\s+(CEO|CTO|ADMIN|ROOT|SUPERUSUARIO)",
            r"(?i)i\s+am\s+(the|a)\s+(CEO|CTO|ADMIN|ROOT|SUPERUSER)",
            r"(?i)actúa como root|actua como root",
            r"(?i)dame privilegios de administrador",
        ]

        for pattern in role_patterns:
            if re.search(pattern, prompt):
                env.add_error("PVC-3A-06", "Simulación de identidad administrativa detectada")
                break

    def _check_response_manipulation(self, prompt: str, response: str, env: ValidationEnvelope) -> None:
        """Verifica si la respuesta ha sido manipulada para esconder algo."""
        if not response:
            return

        # Detectar respuestas demasiado largas (posible distraction)
        if len(response) > 5000:
            env.add_warning("RESP-LONG", "Respuesta excesivamente larga — posible técnica de distracción")

        # Detectar auto-censura en la respuesta
        if re.search(r"(?i)no puedo.*responder|cannot.*answer|ne puedo", response):
            # Esto podría ser legítimo o podría ser que la inyección funcionó
            env.add_warning("RESP-CENSOR", "La respuesta contiene auto-censura — verificar contexto")
