"""Security invariants for safe authentication-related tools."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import paramiko

from retro_audit.tools import (
    BruteForceLogAuditService,
    LockoutSimulationService,
    PasswordStrengthAuditService,
    SshConfigurationAuditService,
    SshCredentialVerificationService,
)


class FakeSshClient:
    def __init__(self, failure: Exception | None = None) -> None:
        self.failure = failure
        self.connect_calls: list[dict[str, object]] = []
        self.policy: object | None = None
        self.closed = False

    def load_system_host_keys(self) -> None:
        pass

    def load_host_keys(self, _path: str) -> None:
        pass

    def set_missing_host_key_policy(self, policy: object) -> None:
        self.policy = policy

    def connect(self, **kwargs: object) -> None:
        self.connect_calls.append(kwargs)
        if self.failure:
            raise self.failure

    def close(self) -> None:
        self.closed = True


class SshCredentialTests(unittest.TestCase):
    def test_uses_one_password_attempt_and_never_discloses_secret(self) -> None:
        secret = "correct horse battery staple"
        client = FakeSshClient(paramiko.AuthenticationException("denied"))
        service = SshCredentialVerificationService(client_factory=lambda: client)  # type: ignore[return-value]
        events: list[str] = []

        result = service.execute(
            "127.0.0.1",
            events.append,
            {"port": "22", "username": "alice", "password": secret},
        )

        self.assertEqual(len(client.connect_calls), 1)
        self.assertFalse(client.connect_calls[0]["allow_agent"])
        self.assertFalse(client.connect_calls[0]["look_for_keys"])
        self.assertIsInstance(client.policy, paramiko.RejectPolicy)
        self.assertTrue(client.closed)
        self.assertNotIn(secret, result.body)
        self.assertNotIn(secret, "\n".join(events))
        self.assertEqual(result.title, "CREDENCIAL SSH RECHAZADA")

    def test_host_key_mismatch_is_rejected_without_retry(self) -> None:
        mismatch = paramiko.BadHostKeyException("host", Mock(), Mock())
        client = FakeSshClient(mismatch)
        service = SshCredentialVerificationService(client_factory=lambda: client)  # type: ignore[return-value]

        result = service.execute(
            "host.example",
            options={"port": "22", "username": "alice", "password": "secret-value"},
        )

        self.assertEqual(len(client.connect_calls), 1)
        self.assertEqual(result.title, "CLAVE SSH NO CONFIABLE")


class FakeAuthTransport:
    def auth_none(self, username: str) -> None:
        if username != "audit-user":
            raise AssertionError("Unexpected username")
        raise paramiko.BadAuthenticationType("not permitted", ["publickey", "password"])


class SshConfigurationTests(unittest.TestCase):
    def test_reports_password_exposure_from_none_query(self) -> None:
        methods = SshConfigurationAuditService._authentication_methods(  # pylint: disable=protected-access
            FakeAuthTransport(),  # type: ignore[arg-type]
            "audit-user",
        )

        self.assertIn("publickey", methods)
        self.assertIn("autenticación por contraseña: expuesta", methods)

    def test_remote_text_is_sanitized(self) -> None:
        rendered = SshConfigurationAuditService._safe_text("SSH-2.0-safe\x1b[31m")  # pylint: disable=protected-access

        self.assertNotIn("\x1b", rendered)


class OfflineAuditTests(unittest.TestCase):
    def test_password_audit_does_not_echo_secret(self) -> None:
        secret = "Unique!Offline#Passphrase42"
        events: list[str] = []

        result = PasswordStrengthAuditService().execute(None, events.append, {"password": secret})

        self.assertNotIn(secret, result.body)
        self.assertNotIn(secret, "\n".join(events))
        self.assertIn("Entropía teórica estimada", result.body)

    def test_lockout_simulation_is_deterministic_and_local(self) -> None:
        result = LockoutSimulationService().execute(
            None,
            options={"failures": "8", "threshold": "5", "window_seconds": "300", "cooldown_seconds": "900"},
        )

        self.assertIn("Bloqueo activado en el intento 5", result.body)
        self.assertIn("Intentos bloqueados: 3", result.body)

    def test_log_detector_aggregates_failed_ssh_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "auth.log"
            path.write_text(
                "Jan 1 host sshd[1]: Failed password for invalid user root from 192.0.2.10 port 123 ssh2\n"
                "Jan 1 host sshd[2]: Failed password for alice from 192.0.2.10 port 124 ssh2\n"
                "Jan 1 host sshd[3]: Failed password for bob from not-an-ip port 125 ssh2\n",
                encoding="utf-8",
            )

            result = BruteForceLogAuditService().execute(
                None,
                options={"path": str(path), "threshold": "2"},
            )

        self.assertIn("192.0.2.10", result.body)
        self.assertIn("root(1)", result.body)
        self.assertNotIn("not-an-ip", result.body)

    def test_log_detector_rejects_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "auth.log"
            link = root / "linked.log"
            source.write_text("", encoding="utf-8")
            link.symlink_to(source)

            result = BruteForceLogAuditService().execute(
                None,
                options={"path": str(link), "threshold": "2"},
            )

        self.assertEqual(result.title, "CONFIGURACIÓN NO VÁLIDA")


if __name__ == "__main__":
    unittest.main()
