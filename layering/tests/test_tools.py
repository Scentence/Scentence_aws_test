from agent.constants import ACCORD_INDEX
from agent.database import PerfumeRepository
from agent.tools import (
    _clash_penalty,
    _harmony_score,
    calculate_compatibility_score,
    calculate_advanced_layering,
    evaluate_pair,
    get_target_vector,
    rank_brand_universal_perfume,
    rank_recommendations,
)


def _sample_pair(repo: PerfumeRepository):
    base = next(iter(repo.all_candidates()))
    candidate = next(iter(repo.all_candidates(exclude_id=base.perfume_id)))
    return base, candidate


def test_get_target_vector_applies_keyword_boost():
    vector = get_target_vector(["citrus", "amber", "floral"])
    assert vector[ACCORD_INDEX["Citrus"]] == 30.0
    assert vector[ACCORD_INDEX["Fresh"]] == 30.0
    assert vector[ACCORD_INDEX["Resinous"]] == 30.0
    assert vector[ACCORD_INDEX["Floral"]] == 30.0


def test_get_target_vector_korean_cool_keywords():
    vector = get_target_vector(["차가운"])
    assert vector[ACCORD_INDEX["Aquatic"]] == 30.0
    assert vector[ACCORD_INDEX["Fresh"]] == 30.0
    assert vector[ACCORD_INDEX["Green"]] == 30.0


def test_calculate_advanced_layering_returns_scores():
    repo = PerfumeRepository()
    base, candidate = _sample_pair(repo)
    target = get_target_vector(["warm"])

    result = calculate_advanced_layering(base, candidate, target)

    assert result.score_breakdown.target >= 0
    assert result.total_score > 0
    assert len(result.spray_order) == 2


def test_rank_recommendations_limits_to_top_three():
    repo = PerfumeRepository()
    base, _ = _sample_pair(repo)
    recommendations, total = rank_recommendations(base.perfume_id, [], repo)

    assert len(recommendations) <= 3
    assert total >= len(recommendations)


def test_calculate_advanced_layering_flags_clash_penalty():
    penalty, clash_detected = _clash_penalty(["Aquatic"], ["Gourmand"])
    assert clash_detected is True
    assert penalty == -1.0


def test_calculate_advanced_layering_blocks_low_target_alignment():
    repo = PerfumeRepository()
    base, candidate = _sample_pair(repo)
    target = [500.0] * len(base.vector)

    result = calculate_advanced_layering(base, candidate, target)

    assert result.feasible is False
    assert result.feasibility_reason == "Target alignment below threshold"


def test_harmony_score_uses_jaccard_thresholds():
    assert _harmony_score(["Amber", "Musk"], ["Amber", "Musk", "Woody"]) == 1.0
    assert _harmony_score(["Amber", "Musk"], ["Amber", "Musk"]) == 0.5
    assert _harmony_score(["Amber"], ["Citrus"]) == 0.0


def test_evaluate_pair_returns_candidate():
    repo = PerfumeRepository()
    result = evaluate_pair("8701", "9300", ["fresh"], repo)

    assert result.perfume_id == "9300"
    assert result.total_score > 0


def test_calculate_compatibility_score_returns_value():
    repo = PerfumeRepository()
    base, candidate = _sample_pair(repo)
    score, feasible = calculate_compatibility_score(base, candidate)

    assert isinstance(score, float)
    assert isinstance(feasible, bool)


def test_rank_brand_universal_perfume_returns_top_pick():
    repo = PerfumeRepository()
    sample = next(iter(repo.all_candidates()))
    brand_perfumes = repo.get_brand_perfumes(sample.perfume_brand)

    best_perfume, avg_score, count = rank_brand_universal_perfume(brand_perfumes, repo)

    assert best_perfume is not None
    assert isinstance(avg_score, float)
    assert isinstance(count, int)


def test_rank_brand_universal_perfume_handles_empty_list():
    repo = PerfumeRepository()
    best_perfume, avg_score, count = rank_brand_universal_perfume([], repo)

    assert best_perfume is None
    assert avg_score == 0.0
    assert count == 0
