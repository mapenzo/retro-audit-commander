"""Integration tests for bounded service banner collection."""

import socket
import threading
import unittest

from retro_audit.factory import AuditServiceFactory
from retro_audit.tools import BannerProbe


class BannerGrabTests(unittest.TestCase):
    def test_collects_and_sanitizes_banner_from_local_service(self) -> None:
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(listener.close)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        port = listener.getsockname()[1]
        received: list[bytes] = []

        def serve_once() -> None:
            connection, _address = listener.accept()
            with connection:
                received.append(connection.recv(128))
                connection.sendall(b"DemoService/1.2\x1b[31m\r\n")

        server = threading.Thread(target=serve_once, daemon=True)
        server.start()
        tool = AuditServiceFactory.create_banner_service(
            probes=(BannerProbe(port, "DEMO", b"VERSION\r\n"),)
        )
        events: list[str] = []
        result = tool.execute("127.0.0.1", events.append)
        server.join(timeout=2)

        self.assertFalse(server.is_alive())
        self.assertEqual(received, [b"VERSION\r\n"])
        self.assertEqual(result.title, "BANNER GRABBING COMPLETADO")
        self.assertIn("DemoService/1.2", result.body)
        self.assertNotIn("\x1b", result.body)
        self.assertTrue(any("respondió" in event for event in events))

    def test_rejects_url_credentials_before_connecting(self) -> None:
        tool = AuditServiceFactory.create_banner_service()
        result = tool.execute("https://user:secret@example.test")
        self.assertEqual(result.title, "OBJETIVO NO VÁLIDO")
        self.assertNotIn("secret", result.body)


if __name__ == "__main__":
    unittest.main()
