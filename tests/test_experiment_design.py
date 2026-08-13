import sys
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from experiment_design import calculate_required_days, calculate_sample_size_per_variant


class ExperimentDesignTests(unittest.TestCase):
    def test_sample_size_targets_requested_relative_mde(self) -> None:
        plan = calculate_sample_size_per_variant(
            baseline_rate=0.01,
            relative_mde=0.20,
        )

        self.assertEqual(plan.target_rate, 0.012)
        self.assertGreater(plan.sample_size_per_variant, 1)

    def test_smaller_effect_requires_larger_sample(self) -> None:
        smaller_effect_plan = calculate_sample_size_per_variant(0.01, 0.10)
        larger_effect_plan = calculate_sample_size_per_variant(0.01, 0.20)

        self.assertGreater(
            smaller_effect_plan.sample_size_per_variant,
            larger_effect_plan.sample_size_per_variant,
        )

    def test_required_days_rounds_up(self) -> None:
        required_days = calculate_required_days(
            sample_size_per_variant=101,
            eligible_exposures_per_day=100,
            variant_allocation=0.50,
        )

        self.assertEqual(required_days, 3)

    def test_invalid_baseline_rate_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            calculate_sample_size_per_variant(0, 0.20)


if __name__ == "__main__":
    unittest.main()
