"""Portable perfume layering constants.

These values are sourced from docs/request.md and shared across the
layering service. Accord ordering is critical because vectors rely on a
fixed index per accord.
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Set, Tuple

ACCORDS: List[str] = [
    "Fresh",
    "Citrus",
    "Fruity",
    "Sweet",
    "Floral",
    "Powdery",
    "Creamy",
    "Gourmand",
    "Oriental",
    "Spicy",
    "Animal",
    "Leathery",
    "Smoky",
    "Woody",
    "Resinous",
    "Earthy",
    "Chypre",
    "Fougère",
    "Green",
    "Aquatic",
    "Synthetic",
]

ACCORD_INDEX: Dict[str, int] = {name: idx for idx, name in enumerate(ACCORDS)}

PERSISTENCE_MAP: Dict[str, int] = {
    "Leathery": 10,
    "Animal": 9,
    "Oriental": 9,
    "Resinous": 9,
    "Smoky": 9,
    "Woody": 9,
    "Earthy": 8,
    "Gourmand": 8,
    "Spicy": 7,
    "Chypre": 7,
    "Fougère": 7,
    "Powdery": 6,
    "Creamy": 6,
    "Sweet": 6,
    "Floral": 5,
    "Synthetic": 5,
    "Fruity": 4,
    "Green": 4,
    "Fresh": 3,
    "Aquatic": 3,
    "Citrus": 2,
}

BASE_NOTES: Tuple[str, ...] = (
    "Woody",
    "Oriental",
    "Animal",
    "Leathery",
    "Resinous",
    "Earthy",
    "Smoky",
)
BASE_NOTE_SET: Set[str] = set(BASE_NOTES)
BASE_NOTE_INDEXES: Tuple[int, ...] = tuple(ACCORD_INDEX[name] for name in BASE_NOTES)

CLASH_PAIRS: Tuple[Tuple[Set[str], Set[str]], ...] = (
    ({"Aquatic"}, {"Gourmand", "Sweet"}),
    ({"Animal"}, {"Green", "Fresh"}),
    ({"Synthetic"}, {"Earthy"}),
    ({"Aquatic"}, {"Oriental", "Spicy"}),
)

KEYWORD_MAP: Dict[str, Sequence[str]] = {
    "citrus": ["Citrus", "Fresh"],
    "cool": ["Aquatic", "Fresh", "Green"],
    "warm": ["Oriental", "Spicy", "Resinous"],
    "sweet": ["Gourmand", "Sweet", "Fruity"],
    "amber": ["Resinous"],
}

KEYWORD_VECTOR_BOOST: float = 30.0


def accord_index(name: str) -> int:
    """Return the configured index for an accord, raising if missing."""

    return ACCORD_INDEX[name]


def base_note_indices() -> Tuple[int, ...]:
    """Return tuple of indexes representing the base note subvector."""

    return BASE_NOTE_INDEXES
