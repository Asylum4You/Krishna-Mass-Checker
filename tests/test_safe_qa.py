import unittest
from datetime import datetime, timezone

from sandbox.audit_log import build_audit_event
from sandbox.browser_qa import BrowserQAProfile
from sandbox.network_config import resolve_approved_proxy
from sandbox.policy_guard import assert_synthetic_payload, simulation_label
from sandbox.session_isolation import create_synthetic_session


class ApprovedProxyTests(unittest.TestCase):
    def test_accepts_only_explicitly_allowlisted_https_host(self):
        result = resolve_approved_proxy("https://qa-proxy.example.test:443", {"qa-proxy.example.test"})
        self.assertEqual(result.host, "qa-proxy.example.test")

    def test_rejects_unapproved_or_unsafe_proxy_urls(self):
        for url, hosts in (
            ("https://other.example.test", {"qa-proxy.example.test"}),
            ("socks5://qa-proxy.example.test", {"qa-proxy.example.test"}),
            ("https://user:pass@qa-proxy.example.test", {"qa-proxy.example.test"}),
            ("https://qa-proxy.example.test/path", {"qa-proxy.example.test"}),
        ):
            with self.subTest(url=url), self.assertRaises(ValueError):
                resolve_approved_proxy(url, hosts)

    def test_no_proxy_is_valid(self):
        self.assertIsNone(resolve_approved_proxy(None, set()))


class BrowserQATests(unittest.TestCase):
    def test_default_presentation_profile(self):
        profile = BrowserQAProfile()
        self.assertEqual(profile.color_scheme, "light")
        self.assertEqual(profile.viewport_width, 1365)

    def test_rejects_unreasonable_viewport_and_unknown_color_scheme(self):
        with self.assertRaises(ValueError):
            BrowserQAProfile(viewport_width=100)
        with self.assertRaises(ValueError):
            BrowserQAProfile(color_scheme="spoofed")


class SyntheticSessionTests(unittest.TestCase):
    def test_sessions_are_distinct_and_ephemeral(self):
        first = create_synthetic_session("case_01")
        second = create_synthetic_session("case_01")
        self.assertNotEqual(first.session_id, second.session_id)
        self.assertEqual(first.storage_mode, "IN_MEMORY_ONLY")
        self.assertEqual(first.mode, "SIMULATION ONLY")

    def test_rejects_non_opaque_test_id(self):
        with self.assertRaises(ValueError):
            create_synthetic_session("4111111111111111")


class AuditLogTests(unittest.TestCase):
    def test_builds_utc_audit_event(self):
        event = build_audit_event(
            test_id="case_01",
            environment="local",
            outcome="passed",
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        self.assertEqual(event["mode"], "SIMULATION ONLY")
        self.assertTrue(event["timestamp"].endswith("+00:00"))

    def test_rejects_sensitive_or_unstructured_fields(self):
        with self.assertRaises(ValueError):
            build_audit_event(test_id="4111111111111111", environment="local", outcome="passed")


class PolicyGuardTests(unittest.TestCase):
    def test_accepts_synthetic_case(self):
        assert_synthetic_payload({"test_id": "case_01", "scenario": "challenge_required"})

    def test_rejects_card_fields_and_pan_like_values(self):
        for payload in (
            {"test_id": "case_01", "card_number": "redacted"},
            {"test_id": "case_01", "metadata": {"cvv": "redacted"}},
            {"test_id": "case_01", "note": "4111111111111111"},
        ):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                assert_synthetic_payload(payload)

    def test_simulation_label_is_explicit(self):
        self.assertIn("SIMULATION ONLY", simulation_label())


if __name__ == "__main__":
    unittest.main()
