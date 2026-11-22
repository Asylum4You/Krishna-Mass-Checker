import unittest

from main import format_bin_info, validate_bin_prefix


class ValidateBinPrefixTests(unittest.TestCase):
    def test_accepts_six_to_eight_digit_prefixes(self):
        self.assertEqual(validate_bin_prefix("411111"), "411111")
        self.assertEqual(validate_bin_prefix(" 41111100 "), "41111100")

    def test_rejects_short_or_long_values(self):
        for value in ("12345", "123456789", ""):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_bin_prefix(value)

    def test_rejects_non_numeric_and_card_like_input(self):
        for value in ("abcdef", "411111 111111 1111", "411111-1", "411111/12"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                validate_bin_prefix(value)


class FormatBinInfoTests(unittest.TestCase):
    def test_formats_public_metadata_and_handles_missing_fields(self):
        result = format_bin_info(
            "411111",
            {
                "scheme": "visa",
                "brand": "Visa Classic",
                "type": "debit",
                "number": {"length": 16},
                "country": {"name": "United States"},
                "bank": {"name": "Example Bank", "url": "example.test"},
            },
        )
        self.assertIn("BIN/IIN prefix: 411111", result)
        self.assertIn("Bank / issuer: Example Bank", result)
        self.assertNotIn("VBV", result)

        missing = format_bin_info("411111", {})
        self.assertIn("Country: Not available", missing)


if __name__ == "__main__":
    unittest.main()
