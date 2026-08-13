from collections import Counter, defaultdict
from collections.abc import Iterable


def build_co_visit_candidates(
    session_item_sequences: Iterable[Iterable[int]],
    max_items_per_session: int = 50,
) -> dict[int, list[int]]:
    """Rank items by how often they co-occur with an anchor item in a session."""
    co_visit_counts: dict[int, Counter[int]] = defaultdict(Counter)

    for sequence in session_item_sequences:
        unique_items = list(dict.fromkeys(sequence))
        if len(unique_items) < 2:
            continue

        limited_items = unique_items[:max_items_per_session]
        for anchor_item in limited_items:
            for candidate_item in limited_items:
                if anchor_item != candidate_item:
                    co_visit_counts[anchor_item][candidate_item] += 1

    return {
        anchor_item: [
            candidate_item
            for candidate_item, _ in sorted(
                candidate_counts.items(),
                key=lambda pair: (-pair[1], pair[0]),
            )
        ]
        for anchor_item, candidate_counts in co_visit_counts.items()
    }


def rank_popular_items(session_item_sequences: Iterable[Iterable[int]]) -> list[int]:
    """Rank items by the number of training sessions in which they appeared."""
    item_counts: Counter[int] = Counter()

    for sequence in session_item_sequences:
        item_counts.update(set(sequence))

    return [
        itemid
        for itemid, _ in sorted(
            item_counts.items(),
            key=lambda pair: (-pair[1], pair[0]),
        )
    ]


def recommend_items(
    anchor_item: int,
    candidates_by_item: dict[int, list[int]],
    top_k: int,
) -> list[int]:
    """Return up to top_k co-visited items for one anchor item."""
    return candidates_by_item.get(anchor_item, [])[:top_k]
