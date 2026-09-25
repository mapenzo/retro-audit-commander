"""Bounded local analysis of SSH authentication-failure logs."""

from __future__ import annotations

import ipaddress
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Mapping

from retro_audit.contracts import ActivityReporter, CheckResult, ToolField, ToolGuide, resolve_reporter

MAX_LOG_BYTES = 5 * 1024 * 1024
FAILED_PASSWORD = re.compile(
    r"Failed password for (?:invalid user )?(?P<user>[^ ]{1,64}) from (?P<ip>[^ ]{1,64}) port \d+"
)


class BruteForceLogAuditService:
    """Detect repeated failed SSH logins in one bounded, local regular file."""

    tool_id = "brute-force-logs"
    display_name = "Detectar fuerza bruta en logs"
    shortcut = "F10"
    guide = ToolGuide(
        purpose="Busca patrones de contraseñas SSH fallidas y agrupa posibles orígenes de fuerza bruta.",
        steps=(
            "Indica la ruta de un auth.log local y regular; no se aceptan enlaces simbólicos.",
            "Define cuántos fallos desde una IP deben generar una alerta.",
            "Ejecuta y revisa los orígenes y usuarios más repetidos.",
        ),
        output="Lista hasta 50 IP sospechosas, número de fallos y tres usuarios frecuentes por origen.",
        safety="Sólo lee localmente archivos de hasta 5 MiB; no bloquea IP, no modifica logs ni contacta hosts.",
    )
    requires_target = False
    requires_authorization = False
    input_fields = (
        ToolField("path", "Ruta local del log", placeholder="/var/log/auth.log"),
        ToolField("threshold", "Umbral de alerta por IP", default="5"),
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
            path = self._validated_path(values.get("path", ""))
            threshold = self._threshold(values.get("threshold", "5"))
        except ValueError as error:
            return CheckResult("CONFIGURACIÓN NO VÁLIDA", str(error))

        safe_filename = self._safe_filename(path.name)
        reporter(f"> Analizando localmente {safe_filename} con lectura limitada...")
        counts: Counter[str] = Counter()
        users: defaultdict[str, Counter[str]] = defaultdict(Counter)
        matched = 0
        try:
            with path.open("r", encoding="utf-8", errors="replace") as stream:
                for line in stream:
                    match = FAILED_PASSWORD.search(line)
                    if match is None or not self._valid_ip(match["ip"]):
                        continue
                    ip = match["ip"]
                    user = self._safe_username(match["user"])
                    counts[ip] += 1
                    users[ip][user] += 1
                    matched += 1
        except OSError:
            return CheckResult("LECTURA DE LOG FALLIDA", "No se pudo leer el archivo local seleccionado.")

        suspects = [(ip, count) for ip, count in counts.most_common() if count >= threshold]
        rows = [
            f"Archivo: {safe_filename}",
            f"Fallos SSH reconocidos: {matched}",
            f"Umbral por IP: {threshold}",
            "",
            "ORIGEN             FALLOS  USUARIOS MÁS FRECUENTES",
        ]
        if suspects:
            for ip, count in suspects[:50]:
                top_users = ", ".join(f"{user}({total})" for user, total in users[ip].most_common(3))
                rows.append(f"{ip:<19} {count:<7} {top_users}")
        else:
            rows.append("No se detectaron orígenes por encima del umbral.")
        if len(suspects) > 50:
            rows.append(f"... {len(suspects) - 50} orígenes adicionales omitidos.")
        reporter(f"+ Análisis finalizado: {len(suspects)} origen(es) sospechoso(s).")
        return CheckResult("ANÁLISIS DEFENSIVO DE LOGS", "\n".join(rows))

    @staticmethod
    def _validated_path(raw_path: str) -> Path:
        if not raw_path.strip():
            raise ValueError("La ruta del log es obligatoria.")
        path = Path(raw_path).expanduser()
        if path.is_symlink() or not path.is_file():
            raise ValueError("El log debe ser un archivo regular y no un enlace simbólico.")
        if path.stat().st_size > MAX_LOG_BYTES:
            raise ValueError("El log supera el límite de 5 MiB.")
        return path

    @staticmethod
    def _threshold(raw_value: str) -> int:
        try:
            value = int(raw_value)
        except ValueError as error:
            raise ValueError("El umbral debe ser numérico.") from error
        if not 2 <= value <= 10000:
            raise ValueError("El umbral debe estar entre 2 y 10000.")
        return value

    @staticmethod
    def _valid_ip(candidate: str) -> bool:
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            return False
        return True

    @staticmethod
    def _safe_username(username: str) -> str:
        return re.sub(r"[^A-Za-z0-9_.@-]", "?", username)[:64]

    @staticmethod
    def _safe_filename(filename: str) -> str:
        return re.sub(r"[\x00-\x1f\x7f]", "?", filename)[:255]
