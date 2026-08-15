import sys
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from ab_analysis import compare_proportions, sample_ratio_mismatch_p_value


class ABAnalysisTests(unittest.TestCase):
    def test_equal_assignment_has_no_sample_ratio_mismatch(self) -> None:
        p_value = sample_ratio_mismatch_p_value(1_000, 1_000)

        self.assertEqual(p_value, 1.0)

    def test_positive_difference_has_positive_confidence_interval(self) -> None:
        comparison = compare_proportions(
            control_successes=50,
            control_total=1_000,
            treatment_successes=100,
            treatment_total=1_000,
        )

        self.assertGreater(comparison.absolute_difference, 0)
        self.assertGreater(comparison.confidence_interval_low, 0)

    def test_newcombe_interval_matches_reference_calculation(self) -> None:
        comparison = compare_proportions(
            control_successes=50,
            control_total=1_000,
            treatment_successes=100,
            treatment_total=1_000,
        )

        self.assertAlmostEqual(
            comparison.confidence_interval_low,
            0.027052228675,
            places=9,
        )
        self.assertAlmostEqual(
            comparison.confidence_interval_high,
            0.073387866330,
            places=9,
        )

    def test_invalid_success_count_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            compare_proportions(
                control_successes=101,
                control_total=100,
                treatment_successes=10,
                treatment_total=100,
            )

    def test_zero_variance_extreme_difference_has_a_small_p_value(self) -> None:
        comparison = compare_proportions(
            control_successes=0,
            control_total=100,
            treatment_successes=100,
            treatment_total=100,
        )

        self.assertLess(comparison.p_value, 0.0001)
        self.assertGreater(comparison.confidence_interval_low, 0)


if __name__ == "__main__":
    unittest.main()
