from agent.constants import ACCORD_INDEX
from agent.database import PerfumeRepository
from agent.tools import calculate_advanced_layering, get_target_vector, rank_recommendations


def test_get_target_vector_applies_keyword_boost():
    vector = get_target_vector(["citrus", "amber"])
    assert vector[ACCORD_INDEX["Citrus"]] == 30.0
    assert vector[ACCORD_INDEX["Fresh"]] == 30.0
    assert vector[ACCORD_INDEX["Resinous"]] == 30.0


def test_calculate_advanced_layering_returns_scores():
    repo = PerfumeRepository()
    base = repo.get_perfume("P001")
    candidate = repo.get_perfume("P002")
    target = get_target_vector(["warm"])

    result = calculate_advanced_layering(base, candidate, target)

    assert result.feasible is True
    assert result.score_breakdown.target > 0
    assert result.total_score > 1.0
    assert len(result.spray_order) == 2


def test_rank_recommendations_limits_to_top_three():
    repo = PerfumeRepository()
    recommendations, total = rank_recommendations("P001", [], repo)

    assert len(recommendations) <= 3
    assert total >= len(recommendations)


def test_calculate_advanced_layering_flags_clash_penalty():
    repo = PerfumeRepository()
    base = repo.get_perfume("P005")
    candidate = repo.get_perfume("P003")
    target = get_target_vector([])

    result = calculate_advanced_layering(base, candidate, target)

    assert result.clash_detected is True
    assert result.score_breakdown.penalty == -1.0


def test_calculate_advanced_layering_blocks_low_target_alignment():
    repo = PerfumeRepository()
    base = repo.get_perfume("P001")
    candidate = repo.get_perfume("P003")
    target = [500.0] * len(base.vector)

    result = calculate_advanced_layering(base, candidate, target)

    assert result.feasible is False
    assert result.feasibility_reason == "Target alignment below threshold"
