"""Security-boundary tests for target parsing and redirect policy."""

import unittest
from urllib.request import Request

from retro_audit.targets import TargetParser, TargetValidationError
from retro_audit.tools.http_headers import RedirectScopeError, SameOriginRedirectHandler


class TargetParserTests(unittest.TestCase):
    def test_web_target_is_normalized_and_redacted(self) -> None:
        target = TargetParser.parse_web("HTTPS://Example.COM:443/path?token=secret#fragment")
        self.assertEqual(target.request_url, "https://example.com/path?token=secret")
        self.assertEqual(target.display_url, "https://example.com/path")

    def test_embedded_credentials_are_rejected(self) -> None:
        with self.assertRaises(TargetValidationError):
            TargetParser.parse_web("https://user:secret@example.com")

    def test_control_characters_are_rejected(self) -> None:
        with self.assertRaises(TargetValidationError):
            TargetParser.parse_web("https://example.com/\nInjected")

    def test_tls_requires_https(self) -> None:
        with self.assertRaises(TargetValidationError):
            TargetParser.parse_web("http://example.com", require_https=True)


class RedirectPolicyTests(unittest.TestCase):
    def test_cross_origin_redirect_is_blocked(self) -> None:
        origin = TargetParser.parse_web("https://example.com")
        handler = SameOriginRedirectHandler(origin)
        request = Request(origin.request_url, method="HEAD")
        with self.assertRaises(RedirectScopeError):
            handler.redirect_request(request, None, 302, "Found", {}, "https://internal.example/")

    def test_https_downgrade_is_blocked(self) -> None:
        origin = TargetParser.parse_web("https://example.com")
        handler = SameOriginRedirectHandler(origin)
        request = Request(origin.request_url, method="HEAD")
        with self.assertRaises(RedirectScopeError):
            handler.redirect_request(request, None, 302, "Found", {}, "http://example.com/")


if __name__ == "__main__":
    unittest.main()
