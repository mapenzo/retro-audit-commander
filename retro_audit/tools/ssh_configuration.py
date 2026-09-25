"""Low-impact SSH negotiation and authentication-method exposure audit."""

from __future__ import annotations

import base64
import hashlib
import re
import socket
from typing import Mapping

import paramiko

from retro_audit.contracts import ActivityReporter, CheckResult, ToolField, ToolGuide, resolve_reporter
from retro_audit.targets import TargetParser, TargetValidationError


class SshConfigurationAuditService:
    """Inspect negotiated SSH properties without trying any credential."""

    tool_id = "ssh-config"
    display_name = "Auditar configuración SSH"
    shortcut = "F8"
    guide = ToolGuide(
        purpose="Inspecciona versión, cifrado, MAC, clave de host y métodos anunciados por SSH.",
        steps=(
            "Introduce el host o IP y confirma la autorización.",
            "Indica el puerto SSH; el usuario es opcional y sólo sirve para consultar métodos.",
            "Ejecuta y revisa algoritmos, huella y exposición de autenticación por contraseña.",
        ),
        output="Muestra negociación SSH, tipo y huella de clave, y métodos de autenticación disponibles.",
        safety="No prueba contraseñas. Si proporcionas usuario, realiza únicamente una consulta auth-none registrable.",
    )
    requires_target = True
    requires_authorization = True
    input_fields = (
        ToolField("port", "Puerto SSH", default="22"),
        ToolField(
            "username",
            "Usuario para consultar métodos (opcional)",
            placeholder="Vacío: no consultar métodos de autenticación",
            required=False,
        ),
    )

    def __init__(self, timeout: float = 5.0) -> None:
        self.timeout = timeout

    def execute(
        self,
        target: str | None,
        report: ActivityReporter | None = None,
        options: Mapping[str, str] | None = None,
    ) -> CheckResult:
        reporter = resolve_reporter(report)
        try:
            hostname = TargetParser.parse_host(target or "")
            port = self._parse_port((options or {}).get("port", "22"))
            username = self._validated_username((options or {}).get("username", "").strip())
        except (TargetValidationError, ValueError) as error:
            return CheckResult("CONFIGURACIÓN NO VÁLIDA", str(error))

        reporter(f"> Negociando SSH de forma defensiva con {hostname}:{port}...")
        transport: paramiko.Transport | None = None
        try:
            connection = socket.create_connection((hostname, port), timeout=self.timeout)
            connection.settimeout(self.timeout)
            transport = paramiko.Transport(connection)
            transport.start_client(timeout=self.timeout)
            key = transport.get_remote_server_key()
            fingerprint = base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode("ascii").rstrip("=")
            methods = self._authentication_methods(transport, username)
            rows = (
                f"Objetivo: {hostname}:{port}",
                f"Versión remota: {self._safe_text(transport.remote_version)}",
                f"Cifrado negociado: {transport.remote_cipher}",
                f"MAC negociado: {transport.remote_mac}",
                f"Clave del host: {key.get_name()}",
                f"Huella SHA256: {fingerprint}",
                f"Métodos de autenticación: {methods}",
            )
        except (OSError, EOFError, paramiko.SSHException):
            reporter("! No fue posible completar la negociación SSH.")
            return CheckResult("AUDITORÍA SSH INCOMPLETA", "El servicio no respondió o la negociación SSH falló.")
        finally:
            if transport is not None:
                transport.close()

        reporter("+ Auditoría de configuración SSH completada sin probar credenciales.")
        return CheckResult("CONFIGURACIÓN SSH AUDITADA", "\n".join(rows))

    @staticmethod
    def _authentication_methods(transport: paramiko.Transport, username: str) -> str:
        if not username:
            return "no consultados (requiere usuario explícito; no se probaron credenciales)"
        try:
            transport.auth_none(username)
        except paramiko.BadAuthenticationType as error:
            methods = sorted(SshConfigurationAuditService._safe_text(method) for method in error.allowed_types)
            password = "expuesta" if "password" in methods else "no anunciada"
            return f"{', '.join(methods) or 'ninguno'}; autenticación por contraseña: {password}"
        except paramiko.AuthenticationException:
            return "el servidor rechazó la consulta sin anunciar métodos"
        return "autenticación sin credenciales aceptada (configuración crítica)"

    @staticmethod
    def _parse_port(raw_port: str) -> int:
        try:
            port = int(raw_port)
        except ValueError as error:
            raise ValueError("El puerto SSH debe ser numérico.") from error
        if not 1 <= port <= 65535:
            raise ValueError("El puerto SSH debe estar entre 1 y 65535.")
        return port

    @staticmethod
    def _validated_username(username: str) -> str:
        if len(username) > 255 or re.search(r"[\x00-\x1f\x7f]", username):
            raise ValueError("El usuario SSH contiene caracteres no permitidos.")
        return username

    @staticmethod
    def _safe_text(value: str) -> str:
        return re.sub(r"[\x00-\x1f\x7f]", "?", value)[:255]
