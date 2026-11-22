import unittest

from main import build_batch_report, format_bin_info, parse_prefix_file, validate_bin_prefix
from sandbox.bin_classifier import classify_bin_metadata
from sandbox.file_processor import parse_simulation_csv
from sandbox.reporting_engine import build_simulation_report
from sandbox.three_ds_simulator import simulate_3ds
from sandbox.validation_engine import validate_simulation_record



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


class BatchFileTests(unittest.TestCase):
    def test_parses_prefixes_deduplicates_and_skips_header(self):
        prefixes, duplicates = parse_prefix_file("BIN/IIN\n411111\n555555\n411111\n")
        self.assertEqual(prefixes, ["411111", "555555"])
        self.assertEqual(duplicates, 1)

    def test_rejects_full_card_like_values_and_multiple_columns(self):
        for content in ("4111111111111111\n", "411111,Example Bank\n", "abcdef\n"):
            with self.subTest(content=content), self.assertRaises(ValueError):
                parse_prefix_file(content)

    def test_enforces_batch_limit(self):
        content = "\n".join(str(400000 + i) for i in range(11))
        with self.assertRaises(ValueError):
            parse_prefix_file(content)

    def test_rejects_empty_file(self):
        with self.assertRaises(ValueError):
            parse_prefix_file("\n")


class FormatBinInfoTests(unittest.TestCase):
    def test_formats_public_metadata_and_marks_authentication_untested(self):
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
        self.assertIn("3-D Secure / VBV status: Not tested", result)

        missing = format_bin_info("411111", {})
        self.assertIn("Country: Not available", missing)


class BatchReportTests(unittest.TestCase):
    def test_report_contains_only_prefix_metadata_and_not_tested_status(self):
        report = build_batch_report([{
            "BIN/IIN prefix": "411111",
            "Scheme": "visa",
            "Brand": "Visa",
            "Card type": "debit",
            "Country": "United States",
            "Bank / issuer": "Example Bank",
            "Lookup result": "Found",
            "3-D Secure / VBV status": "Not tested",
        }]).decode("utf-8")
        self.assertIn("411111", report)
        self.assertIn("Not tested", report)
        self.assertNotIn("4111111111111111", report)


if __name__ == "__main__":
    unittest.main()


from sandbox.bin_classifier import classify_bin_metadata
from sandbox.file_processor import parse_simulation_csv
from sandbox.reporting_engine import build_simulation_report
from sandbox.three_ds_simulator import simulate_3ds
from sandbox.validation_engine import validate_simulation_record


class SyntheticSimulationTests(unittest.TestCase):
    def test_accepts_only_allowlisted_synthetic_scenarios(self):
        record = validate_simulation_record({"test_id": "case_01", "scenario": "challenge_required"})
        self.assertEqual(record["scenario"], "challenge_required")
        with self.assertRaises(ValueError):
            validate_simulation_record({"test_id": "case_02", "scenario": "real_card_check"})

    def test_rejects_card_fields_and_malformed_records(self):
        with self.assertRaises(ValueError):
            validate_simulation_record({
                "test_id": "case_01", "scenario": "unavailable", "card_number": "4111111111111111"
            })

    def test_simulator_is_explicitly_mocked(self):
        result = simulate_3ds("frictionless_success")
        self.assertEqual(result["result"], "SIMULATED_AUTHENTICATED")
        self.assertIn("SIMULATION ONLY", result["mode"])
        with self.assertRaises(ValueError):
            simulate_3ds("411111")

    def test_parses_synthetic_batch_and_rejects_duplicate_ids(self):
        parsed = parse_simulation_csv(
            "test_id,scenario\\ncase_1,frictionless_success\\ncase_2,challenge_failed\\n"
        )
        self.assertEqual(len(parsed), 2)
        with self.assertRaises(ValueError):
            parse_simulation_csv("test_id,scenario\\ncase_1,unavailable\\ncase_1,not_enrolled\\n")

    def test_rejects_extra_csv_fields(self):
        with self.assertRaises(ValueError):
            parse_simulation_csv("test_id,scenario,pan\\ncase_1,unavailable,4111111111111111\\n")

    def test_simulation_report_labels_all_results_as_mock(self):
        result = simulate_3ds("not_enrolled")
        report = build_simulation_report([{"test_id": "case_1", **result}]).decode("utf-8")
        self.assertIn("SIMULATED_NOT_ENROLLED", report)
        self.assertIn("SIMULATION ONLY", report)
        self.assertNotIn("4111111111111111", report)

    def test_bin_classifier_returns_metadata_not_authentication(self):
        result = classify_bin_metadata({
            "scheme": "visa", "country": {"name": "United States"},
            "bank": {"name": "Synthetic Bank"}
        })
        self.assertEqual(result["Scheme"], "visa")
        self.assertEqual(result["3-D Secure / VBV status"], "Not tested")
