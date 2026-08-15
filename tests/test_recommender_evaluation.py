import sys
from pathlib import Path
import unittest

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from run_recommender_evaluation import visitor_bootstrap_hit_rate_interval


class RecommenderEvaluationTests(unittest.TestCase):
    def test_bootstrap_interval_is_independent_of_example_row_order(self) -> None:
        examples = pd.DataFrame(
            [
                {"visitorid": 30, "anchor_itemid": 10, "target_itemid": 20},
                {"visitorid": 10, "anchor_itemid": 10, "target_itemid": 40},
                {"visitorid": 20, "anchor_itemid": 10, "target_itemid": 20},
            ]
        )
        candidates = {10: [20]}

        original_order_interval = visitor_bootstrap_hit_rate_interval(
            candidates,
            examples,
        )
        shuffled_order_interval = visitor_bootstrap_hit_rate_interval(
            candidates,
            examples.sample(frac=1, random_state=2026),
        )

        self.assertEqual(original_order_interval, shuffled_order_interval)


if __name__ == "__main__":
    unittest.main()
