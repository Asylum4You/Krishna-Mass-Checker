"""Unit tests for safe public metadata classification."""
import unittest

from sandbox.bin_classifier import classify_bin_metadata


class BinClassifierTests(unittest.TestCase):
    def test_rich_metadata_is_provider_reported_not_verified(self):
        result = classify_bin_metadata({
            "scheme": "visa", "type": "debit", "brand": "Classic",
            "country": {"name": "United States", "alpha2": "US"},
            "bank": {"name": "Example Bank"},
        }, retrieved_at="2026-11-22T00:00:00+00:00")
        self.assertEqual(result["network"], "visa")
        self.assertEqual(result["funding_type"], "debit")
        self.assertEqual(result["metadata_confidence"], "provider_reported_rich")
        self.assertEqual(result["security_posture"], "metadata_consistent")
        self.assertEqual(result["real_card_3ds_status"], "unknown")
        self.assertEqual(result["authentication_status"], "not_tested")

    def test_missing_fields_are_unknown(self):
        result = classify_bin_metadata({})
        self.assertEqual(result["network"], "unknown")
        self.assertEqual(result["funding_type"], "unknown")
        self.assertEqual(result["security_posture"], "no_classifiable_metadata")
        self.assertEqual(result["metadata_confidence"], "insufficient_metadata")

    def test_conflicting_metadata_is_flagged(self):
        result = classify_bin_metadata({
            "scheme": "madeup-network", "type": "credit",
            "prepaid": True, "country": {"alpha2": "USA"}
        })
        self.assertEqual(result["security_posture"], "metadata_inconsistent")
        self.assertIn("unrecognized_network_value", result["quality_flags"])
        self.assertIn("invalid_country_code", result["quality_flags"])
        self.assertIn("prepaid_credit_metadata_conflict", result["quality_flags"])

    def test_does_not_infer_authentication_from_metadata(self):
        result = classify_bin_metadata({
            "scheme": "mastercard", "type": "credit",
            "authentication_status": "passed", "three_ds": True
        })
        self.assertEqual(result["authentication_status"], "not_tested")
        self.assertEqual(result["real_card_3ds_status"], "unknown")


if __name__ == "__main__":
    unittest.main()
