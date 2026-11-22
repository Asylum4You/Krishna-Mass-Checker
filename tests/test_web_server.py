import unittest
from unittest.mock import patch

from web_server import _allow_request, normalize_metadata, validate_prefix


class WebCheckerValidationTests(unittest.TestCase):
    def test_accepts_only_six_to_eight_digit_prefixes(self):
        self.assertEqual(validate_prefix("411111"), "411111")
        self.assertEqual(validate_prefix("41111100"), "41111100")
        for value in ("12345", "123456789", "4111111111111111", "abcdef", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_prefix(value)

    def test_metadata_is_reduced_to_public_allowlist(self):
        result = normalize_metadata({
            "scheme": "visa", "type": "debit", "brand": "Visa",
            "bank": {"name": "Example Bank", "url": "https://example.test", "phone": "123"},
            "country": {"name": "United States", "alpha2": "US", "latitude": 1},
            "number": {"length": 16, "luhn": True, "other": "ignored"},
            "prepaid": False, "extra": "ignored",
        })
        self.assertEqual(result["bank"], {"name": "Example Bank"})
        self.assertEqual(result["country"], {"name": "United States", "alpha2": "US"})
        self.assertEqual(result["number"], {"length": 16, "luhn": True})
        self.assertEqual(result["authentication_status"], "Not tested")
        self.assertNotIn("extra", result)
        self.assertNotIn("url", result["bank"])

    def test_rate_limit_is_bounded_per_client(self):
        client = "unit-test-client"
        with patch("web_server.RATE_MAX_REQUESTS", 2):
            self.assertTrue(_allow_request(client, now=100.0))
            self.assertTrue(_allow_request(client, now=101.0))
            self.assertFalse(_allow_request(client, now=102.0))
            self.assertTrue(_allow_request(client, now=161.0))


if __name__ == "__main__":
    unittest.main()
