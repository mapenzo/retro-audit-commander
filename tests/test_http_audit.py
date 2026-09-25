"""Behavioral tests for the low-impact HTTP audit."""

import unittest
from email.message import Message
from unittest.mock import patch
from urllib.error import HTTPError

from retro_audit.tools.http_headers import HttpHeaderAuditService


class RateLimitedOpener:
    def __init__(self) -> None:
        self.calls = 0
        self.method = ""

    def open(self, request, timeout: int):  # type: ignore[no-untyped-def]  # pylint: disable=unused-argument
        self.calls += 1
        self.method = request.get_method()
        headers = Message()
        headers["Retry-After"] = "120"
        headers["X-Frame-Options"] = "DENY"
        raise HTTPError(request.full_url, 429, "Too Many Requests", headers, None)


class HttpAuditTests(unittest.TestCase):
    def test_rate_limit_is_not_retried_and_query_is_redacted(self) -> None:
        opener = RateLimitedOpener()
        events: list[str] = []
        with patch("retro_audit.tools.http_headers.build_opener", return_value=opener):
            result = HttpHeaderAuditService().inspect("https://example.test/path?token=secret", events.append)

        self.assertEqual(opener.calls, 1)
        self.assertEqual(opener.method, "HEAD")
        self.assertEqual(result.title, "AUDITORÍA HTTP PARCIAL (429)")
        self.assertIn("RETRY-AFTER: 120", result.body)
        self.assertNotIn("secret", result.body)


if __name__ == "__main__":
    unittest.main()
