import sys
from pathlib import Path
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from item_recommender import (
    build_co_visit_candidates,
    rank_popular_items,
    recommend_items,
)


class ItemRecommenderTests(unittest.TestCase):
    def test_candidates_exclude_the_anchor_item(self) -> None:
        candidates = build_co_visit_candidates([[10, 20, 10], [10, 30]])

        self.assertNotIn(10, candidates[10])

    def test_candidates_rank_higher_frequency_first(self) -> None:
        candidates = build_co_visit_candidates([[10, 20], [10, 20], [10, 30]])

        self.assertEqual(candidates[10], [20, 30])

    def test_recommendations_respect_top_k_and_unknown_items(self) -> None:
        candidates = {10: [20, 30, 40]}

        self.assertEqual(recommend_items(10, candidates, top_k=2), [20, 30])
        self.assertEqual(recommend_items(99, candidates, top_k=2), [])

    def test_popular_items_rank_by_distinct_session_frequency(self) -> None:
        popular_items = rank_popular_items([[10, 10, 20], [10, 30], [20, 30]])

        self.assertEqual(popular_items, [10, 20, 30])


if __name__ == "__main__":
    unittest.main()
