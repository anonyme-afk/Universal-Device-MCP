import unittest

from universal_device_mcp.payload_analysis import analyze_payload


class PayloadAnalysisTests(unittest.TestCase):
    def test_text_and_baseline_comparison_are_hypotheses(self):
        result = analyze_payload("41424344", "41424345")
        self.assertEqual("ABCD", result["utf8_text"])
        self.assertEqual(1.0, result["ascii_printable_ratio"])
        self.assertEqual(3, result["comparison"]["common_prefix_bytes"])
        self.assertEqual({"offset": 3, "baseline": 69, "sample": 68},
                         result["comparison"]["changed_offsets"][0])
        self.assertEqual("hypothesis", result["confidence"])

    def test_payload_size_is_bounded(self):
        with self.assertRaises(ValueError):
            analyze_payload("00" * (1_048_576 + 1))


if __name__ == "__main__":
    unittest.main()
