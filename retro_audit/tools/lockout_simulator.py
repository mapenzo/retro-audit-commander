"""Deterministic, local-only authentication lockout policy simulator."""

from __future__ import annotations

from typing import Mapping

from retro_audit.contracts import ActivityReporter, CheckResult, ToolField, ToolGuide, resolve_reporter


class LockoutSimulationService:
    """Model failed logins in memory without contacting an authentication service."""

    tool_id = "lockout-simulator"
    display_name = "Simular bloqueo local"
    shortcut = "F7"
    guide = ToolGuide(
        purpose="Simula en memoria cómo respondería una política ante varios intentos fallidos.",
        steps=(
            "Indica cuántos fallos quieres simular y el umbral que activa el bloqueo.",
            "Define la ventana de observación y la duración del bloqueo en segundos.",
            "Ejecuta y compara cuántos intentos se procesan y cuántos quedan bloqueados.",
        ),
        output="Explica cuándo se activa el bloqueo y advierte sobre umbrales o duraciones débiles.",
        safety="Es una simulación determinista local: no envía intentos de autenticación a ningún sistema.",
    )
    requires_target = False
    requires_authorization = False
    input_fields = (
        ToolField("failures", "Intentos fallidos simulados", default="5"),
        ToolField("threshold", "Umbral de bloqueo", default="5"),
        ToolField("window_seconds", "Ventana (segundos)", default="300"),
        ToolField("cooldown_seconds", "Duración del bloqueo", default="900"),
    )

    def execute(
        self,
        _target: str | None,
        report: ActivityReporter | None = None,
        options: Mapping[str, str] | None = None,
    ) -> CheckResult:
        reporter = resolve_reporter(report)
        try:
            values = options or {}
            failures = self._bounded_int(values, "failures", 0, 100)
            threshold = self._bounded_int(values, "threshold", 1, 100)
            window = self._bounded_int(values, "window_seconds", 1, 86400)
            cooldown = self._bounded_int(values, "cooldown_seconds", 1, 86400)
        except ValueError as error:
            return CheckResult("POLÍTICA NO VÁLIDA", str(error))

        reporter("> Ejecutando simulación local sin tráfico de autenticación...")
        locked_at = threshold if failures >= threshold else None
        accepted_failures = min(failures, threshold)
        blocked = max(0, failures - threshold) if locked_at else 0
        status = f"Bloqueo activado en el intento {locked_at}." if locked_at else "No se alcanza el umbral de bloqueo."
        observations = []
        if threshold > 5:
            observations.append("! Umbral superior a 5: aumenta la exposición a intentos repetidos.")
        if cooldown < 300:
            observations.append("! Bloqueo inferior a 5 minutos: recuperación potencialmente demasiado rápida.")
        if not observations:
            observations.append("+ La política simulada aplica controles de bloqueo razonables.")
        reporter("+ Simulación de política completada.")
        return CheckResult(
            "SIMULACIÓN LOCAL COMPLETADA",
            "\n".join(
                (
                    f"Intentos simulados: {failures}",
                    f"Umbral: {threshold} fallos en {window} segundos",
                    f"Duración de bloqueo: {cooldown} segundos",
                    f"Fallos procesados antes del bloqueo: {accepted_failures}",
                    f"Intentos bloqueados: {blocked}",
                    f"Resultado: {status}",
                    "",
                    *observations,
                )
            ),
        )

    @staticmethod
    def _bounded_int(values: Mapping[str, str], key: str, minimum: int, maximum: int) -> int:
        try:
            value = int(values.get(key, ""))
        except ValueError as error:
            raise ValueError(f"{key} debe ser un número entero.") from error
        if not minimum <= value <= maximum:
            raise ValueError(f"{key} debe estar entre {minimum} y {maximum}.")
        return value
