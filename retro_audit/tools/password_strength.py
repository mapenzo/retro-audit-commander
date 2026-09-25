"""Offline password-strength assessment that never persists the supplied secret."""

from __future__ import annotations

import math
import re
from typing import Mapping

from retro_audit.contracts import ActivityReporter, CheckResult, ToolField, ToolGuide, resolve_reporter

COMMON_PASSWORDS = frozenset(
    {"123456", "12345678", "password", "password1", "qwerty", "admin", "letmein", "welcome"}
)
SEQUENCES = ("0123456789", "abcdefghijklmnopqrstuvwxyz", "qwertyuiop", "asdfghjkl")
MAX_PASSWORD_CHARACTERS = 4096


class PasswordStrengthAuditService:
    """Estimate password strength locally without network access or secret disclosure."""

    tool_id = "password-strength"
    display_name = "Auditar contraseña offline"
    shortcut = "F6"
    guide = ToolGuide(
        purpose="Evalúa localmente la fortaleza básica de una contraseña sin contactar ningún servidor.",
        steps=(
            "Abre la herramienta; no necesitas objetivo ni autorización de red.",
            "Escribe la contraseña en el campo enmascarado y pulsa EJECUTAR.",
            "Revisa clasificación, longitud, diversidad, patrones detectados y entropía teórica.",
        ),
        output="Muestra una clasificación orientativa y recomendaciones sin revelar la contraseña.",
        safety="El secreto se procesa sólo en memoria y no aparece en eventos, resultados ni informes.",
    )
    requires_target = False
    requires_authorization = False
    input_fields = (ToolField("password", "Contraseña a evaluar", secret=True),)

    def execute(
        self,
        _target: str | None,
        report: ActivityReporter | None = None,
        options: Mapping[str, str] | None = None,
    ) -> CheckResult:
        reporter = resolve_reporter(report)
        password = (options or {}).get("password", "")
        if not password:
            return CheckResult("CONTRASEÑA NO VÁLIDA", "La contraseña es obligatoria.")
        if len(password) > MAX_PASSWORD_CHARACTERS:
            return CheckResult("CONTRASEÑA NO VÁLIDA", "La contraseña supera el límite de 4096 caracteres.")

        reporter("> Evaluando la contraseña exclusivamente en memoria local...")
        classes = sum(
            bool(re.search(pattern, password))
            for pattern in (r"[a-z]", r"[A-Z]", r"[0-9]", r"[^A-Za-z0-9]")
        )
        alphabet = sum(
            size
            for pattern, size in ((r"[a-z]", 26), (r"[A-Z]", 26), (r"[0-9]", 10), (r"[^A-Za-z0-9]", 33))
            if re.search(pattern, password)
        )
        estimate = round(len(password) * math.log2(max(alphabet, 1)), 1)
        normalized = password.casefold()
        findings: list[str] = []
        score = min(4, len(password) // 4) + classes

        if len(password) < 12:
            findings.append("- Longitud inferior a 12 caracteres.")
            score -= 2
        if normalized in COMMON_PASSWORDS:
            findings.append("- Coincide con una contraseña extremadamente común.")
            score = 0
        if any(fragment in sequence for sequence in SEQUENCES for fragment in (normalized, normalized[::-1])):
            findings.append("- Contiene una secuencia predecible.")
            score -= 2
        if re.search(r"(.)\1{2,}", password):
            findings.append("- Contiene caracteres repetidos consecutivamente.")
            score -= 1
        if classes < 3:
            findings.append("- Diversidad limitada de tipos de caracteres.")

        rating = ("MUY DÉBIL", "DÉBIL", "DÉBIL", "MODERADA", "MODERADA", "FUERTE", "FUERTE", "MUY FUERTE")[
            max(0, min(score, 7))
        ]
        if not findings:
            findings.append("+ No se detectaron patrones básicos de alto riesgo.")
        reporter("+ Auditoría offline finalizada; el secreto no se guardó.")
        body = [
            f"Clasificación: {rating}",
            f"Longitud: {len(password)} caracteres",
            f"Clases presentes: {classes} de 4",
            f"Entropía teórica estimada: {estimate} bits (no mide patrones reales)",
            "",
            *findings,
            "",
            "La contraseña no se incluye en este resultado ni se transmite por red.",
        ]
        return CheckResult("AUDITORÍA OFFLINE COMPLETADA", "\n".join(body))
