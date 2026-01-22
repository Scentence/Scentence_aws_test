"""Placeholder for future graph-based orchestration.

This module remains lightweight for now but documents where LangGraph or
similar tooling can hook into the new recommendation utilities.
"""

from __future__ import annotations

from .database import PerfumeRepository
from .tools import rank_recommendations


def preview_layering_paths(base_perfume_id: str, keywords: list[str], repository: PerfumeRepository):
    """Thin wrapper showcasing how graph nodes would invoke the scorer."""

    recommendations, _ = rank_recommendations(base_perfume_id, keywords, repository)
    return recommendations
