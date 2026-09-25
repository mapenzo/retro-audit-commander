"""Single-attempt SSH credential verification with strict host-key checking."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import re
from typing import Mapping

import paramiko

from retro_audit.contracts import ActivityReporter, CheckResult, ToolField, ToolGuide, resolve_reporter
from retro_audit.targets import TargetParser, TargetValidationError


class SshCredentialVerificationService:
    """Verify one authorized SSH credential without retries or credential discovery."""

    tool_id = "ssh-credential"
    display_name = "Verificar credencial SSH"
    shortcut = "F5"
    guide = ToolGuide(
        purpose="Comprueba una sola combinación de usuario y contraseña SSH autorizada.",
        steps=(
            "Introduce el host o IP, confirma la autorización y abre la herramienta.",
            "Indica puerto, usuario y contraseña; opcionalmente selecciona un archivo known_hosts.",
            "Ejecuta una vez. El host debe tener una clave previamente confiable en known_hosts.",
        ),
        output="Indica si la credencial fue aceptada, rechazada o si la clave del host no es confiable.",
        safety="Hace exactamente un intento, no reintenta, no usa ssh-agent y nunca muestra ni guarda la contraseña.",
    )
    requires_target = True
    requires_authorization = True
    input_fields = (
        ToolField("port", "Puerto SSH", default="22"),
        ToolField("username", "Usuario"),
        ToolField("password", "Contraseña", secret=True),
        ToolField(
            "known_hosts",
            "Archivo known_hosts (opcional)",
            placeholder="Vacío: archivos conocidos del sistema/usuario",
            required=False,
        ),
    )

    def __init__(self, client_factory: Callable[[], paramiko.SSHClient] = paramiko.SSHClient) -> None:
        self._client_factory = client_factory

    def execute(
        self,
        target: str | None,
        report: ActivityReporter | None = None,
        options: Mapping[str, str] | None = None,
    ) -> CheckResult:
        reporter = resolve_reporter(report)
        try:
            hostname = TargetParser.parse_host(target or "")
            values = options or {}
            port = self._parse_port(values.get("port", "22"))
            username = self._username(self._required(values, "username"))
            password = self._required(values, "password")
            if len(password) > 4096:
                raise ValueError("La contraseña supera el límite de 4096 caracteres.")
        except (TargetValidationError, ValueError) as error:
            reporter(f"! Configuración SSH no válida: {error}")
            return CheckResult("CONFIGURACIÓN NO VÁLIDA", str(error))

        client = self._client_factory()
        try:
            client.load_system_host_keys()
            known_hosts = values.get("known_hosts", "").strip()
            if known_hosts:
                client.load_host_keys(str(self._validated_known_hosts(known_hosts)))
            client.set_missing_host_key_policy(paramiko.RejectPolicy())
            reporter(f"> Verificando una credencial autorizada en {hostname}:{port} (sin reintentos)...")
            client.connect(
                hostname=hostname,
                port=port,
                username=username,
                password=password,
                timeout=5.0,
                banner_timeout=5.0,
                auth_timeout=5.0,
                allow_agent=False,
                look_for_keys=False,
            )
        except paramiko.BadHostKeyException:
            reporter("! La clave del host no coincide con la clave confiable.")
            return CheckResult("CLAVE SSH NO CONFIABLE", "La clave presentada no coincide con known_hosts.")
        except paramiko.AuthenticationException:
            reporter("! La credencial no fue aceptada; no se realizarán reintentos.")
            return CheckResult("CREDENCIAL SSH RECHAZADA", "Autenticación rechazada tras un único intento.")
        except (OSError, paramiko.SSHException) as error:
            reporter("! No fue posible completar la verificación SSH de forma segura.")
            return CheckResult("VERIFICACIÓN SSH INCOMPLETA", self._safe_error(error))
        finally:
            client.close()

        reporter("+ Credencial SSH aceptada en el único intento autorizado.")
        return CheckResult(
            "CREDENCIAL SSH VÁLIDA",
            f"Host: {hostname}:{port}\nUsuario: {username}\nIntentos realizados: 1\nClave del host: validada",
        )

    @staticmethod
    def _required(values: Mapping[str, str], key: str) -> str:
        value = values.get(key, "").strip()
        if not value:
            raise ValueError(f"El campo {key} es obligatorio.")
        return value

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
    def _username(username: str) -> str:
        if len(username) > 255 or re.search(r"[\x00-\x1f\x7f]", username):
            raise ValueError("El usuario SSH contiene caracteres no permitidos.")
        return username

    @staticmethod
    def _validated_known_hosts(raw_path: str) -> Path:
        path = Path(raw_path).expanduser()
        if path.is_symlink() or not path.is_file():
            raise ValueError("known_hosts debe ser un archivo regular, no un enlace simbólico.")
        return path

    @staticmethod
    def _safe_error(error: Exception) -> str:
        if isinstance(error, paramiko.SSHException):
            return "El servidor no pudo verificarse con las claves conocidas o falló la negociación SSH."
        return "No se pudo establecer la conexión TCP con el servidor SSH."
