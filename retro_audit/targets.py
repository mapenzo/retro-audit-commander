"""Canonical target parsing and validation."""

from dataclasses import dataclass
from urllib.parse import SplitResult, urlsplit, urlunsplit

MAX_TARGET_LENGTH = 2048
ALLOWED_WEB_SCHEMES = frozenset({"http", "https"})


class TargetValidationError(ValueError):
    """Raised when an audit target is malformed or unsafe to process."""


@dataclass(frozen=True)
class WebTarget:
    """Validated web destination with a redacted display URL."""

    request_url: str
    display_url: str
    scheme: str
    hostname: str
    port: int


class TargetParser:
    """Normalize target input consistently across audit tools."""

    @staticmethod
    def _validate_raw(value: str) -> str:
        target = value.strip()
        if not target:
            raise TargetValidationError("El objetivo está vacío.")
        if len(target) > MAX_TARGET_LENGTH:
            raise TargetValidationError("El objetivo supera la longitud permitida.")
        if any(ord(character) < 32 or ord(character) == 127 for character in target):
            raise TargetValidationError("El objetivo contiene caracteres de control.")
        return target

    @staticmethod
    def _normalize_hostname(hostname: str | None) -> str:
        if not hostname or any(character.isspace() for character in hostname):
            raise TargetValidationError("El objetivo no contiene un host válido.")
        try:
            normalized = hostname.encode("idna").decode("ascii").lower()
        except UnicodeError as error:
            raise TargetValidationError("El nombre de host no es válido.") from error
        if len(normalized) > 253:
            raise TargetValidationError("El nombre de host supera la longitud permitida.")
        return normalized

    @classmethod
    def parse_web(cls, value: str, *, require_https: bool = False) -> WebTarget:
        target = cls._validate_raw(value)
        candidate = target if "://" in target else f"https://{target}"
        try:
            parsed = urlsplit(candidate)
            parsed_hostname = parsed.hostname
        except ValueError as error:
            raise TargetValidationError("La URL no es válida.") from error
        scheme = parsed.scheme.lower()
        if scheme not in ALLOWED_WEB_SCHEMES:
            raise TargetValidationError("Sólo se admiten esquemas HTTP y HTTPS.")
        if require_https and scheme != "https":
            raise TargetValidationError("Esta auditoría requiere un objetivo HTTPS.")
        if parsed.username is not None or parsed.password is not None:
            raise TargetValidationError("No se permiten credenciales embebidas en la URL.")
        hostname = cls._normalize_hostname(parsed_hostname)
        try:
            port = parsed.port or (443 if scheme == "https" else 80)
        except ValueError as error:
            raise TargetValidationError("La URL contiene un puerto no válido.") from error

        netloc_host = f"[{hostname}]" if ":" in hostname else hostname
        default_port = 443 if scheme == "https" else 80
        netloc = netloc_host if port == default_port else f"{netloc_host}:{port}"
        path = parsed.path or "/"
        request_url = urlunsplit(SplitResult(scheme, netloc, path, parsed.query, ""))
        display_url = urlunsplit(SplitResult(scheme, netloc, path, "", ""))
        return WebTarget(request_url, display_url, scheme, hostname, port)

    @classmethod
    def parse_host(cls, value: str) -> str:
        target = cls._validate_raw(value)
        try:
            parsed = urlsplit(target if "://" in target else f"//{target}")
            parsed_hostname = parsed.hostname
        except ValueError as error:
            raise TargetValidationError("El host no es válido.") from error
        if parsed.username is not None or parsed.password is not None:
            raise TargetValidationError("No se permiten credenciales en el objetivo.")
        hostname = cls._normalize_hostname(parsed_hostname)
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise TargetValidationError("El escaneo TCP requiere sólo un host o dirección IP.")
        return hostname
