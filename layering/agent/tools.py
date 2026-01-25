"""Core algorithms implementing the portable layering specification."""

from __future__ import annotations

import math
from typing import Iterable, List, Sequence, Tuple

from .constants import (
    ACCORDS,
    ACCORD_INDEX,
    CLASH_PAIRS,
    KEYWORD_MAP,
    KEYWORD_VECTOR_BOOST,
)
from .database import PerfumeRepository
from .schemas import LayeringCandidate, PerfumeVector, ScoreBreakdown
from .tools_schemas import LayeringComputationResult


def get_target_vector(keywords: Sequence[str]) -> List[float]:
    vector = [0.0] * len(ACCORDS)
    for keyword in keywords:
        if keyword is None:
            continue
        normalized = keyword.strip().lower()
        if not normalized:
            continue
        accords = KEYWORD_MAP.get(normalized)
        if not accords:
            continue
        for accord in accords:
            vector[ACCORD_INDEX[accord]] += KEYWORD_VECTOR_BOOST
    return vector


def calculate_advanced_layering(
    base: PerfumeVector,
    candidate: PerfumeVector,
    target_vector: Sequence[float],
) -> LayeringComputationResult:
    penalty, clash_detected = _clash_penalty(base.dominant_accords, candidate.dominant_accords)
    harmony = _harmony_score(base.base_notes, candidate.base_notes)
    bridge = _bridge_bonus(base.vector, candidate.vector)
    target_score = _target_match_score(base.vector, candidate.vector, target_vector)
    feasible, reason = _feasibility_guard(base.vector, target_vector, target_score)
    layered_vector = [
        (base_value + candidate_value) / 2
        for base_value, candidate_value in zip(base.vector, candidate.vector)
    ]
    total_score = 1.0 + harmony + bridge + penalty + target_score
    score_breakdown = ScoreBreakdown(
        harmony=harmony,
        bridge=bridge,
        penalty=penalty,
        target=target_score,
    )
    spray_order = _spray_order(base, candidate)
    return LayeringComputationResult(
        candidate=candidate,
        total_score=total_score,
        feasible=feasible,
        feasibility_reason=reason,
        clash_detected=clash_detected,
        spray_order=spray_order,
        score_breakdown=score_breakdown,
        layered_vector=layered_vector,
    )


def rank_recommendations(
    base_perfume_id: str,
    keywords: Sequence[str],
    repository: PerfumeRepository,
) -> Tuple[List[LayeringCandidate], int]:
    base = repository.get_perfume(base_perfume_id)
    target_vector = get_target_vector(keywords)
    candidates: List[LayeringCandidate] = []
    for candidate in repository.all_candidates(exclude_id=base_perfume_id):
        result = calculate_advanced_layering(base, candidate, target_vector)
        if not result.feasible:
            continue
        candidates.append(_result_to_candidate(result))
    candidates.sort(key=lambda item: item.total_score, reverse=True)
    total_available = len(candidates)
    return candidates[:3], total_available


def evaluate_pair(
    base_perfume_id: str,
    candidate_perfume_id: str,
    keywords: Sequence[str],
    repository: PerfumeRepository,
) -> LayeringCandidate:
    base = repository.get_perfume(base_perfume_id)
    candidate = repository.get_perfume(candidate_perfume_id)
    target_vector = get_target_vector(keywords)
    result = calculate_advanced_layering(base, candidate, target_vector)
    return _result_to_candidate(result)


def _clash_penalty(
    base_dominant: Iterable[str],
    candidate_dominant: Iterable[str],
) -> Tuple[float, bool]:
    base_set = set(base_dominant)
    candidate_set = set(candidate_dominant)
    for left, right in CLASH_PAIRS:
        if (base_set & left and candidate_set & right) or (base_set & right and candidate_set & left):
            return -1.0, True
    return 0.0, False


def _harmony_score(base_notes: Sequence[str], candidate_notes: Sequence[str]) -> float:
    base_set = {note.strip().lower() for note in base_notes if note}
    candidate_set = {note.strip().lower() for note in candidate_notes if note}
    if not base_set or not candidate_set:
        return 0.0
    intersection = base_set & candidate_set
    union = base_set | candidate_set
    similarity = len(intersection) / len(union) if union else 0.0
    if similarity == 0.0:
        return 0.0
    if 0.4 <= similarity <= 0.7:
        return 1.0
    if similarity > 0.7:
        return 0.5
    return 0.0


def _bridge_bonus(base_vector: Sequence[float], candidate_vector: Sequence[float]) -> float:
    bonus = 0.0
    for base_value, candidate_value in zip(base_vector, candidate_vector):
        if 5.0 <= base_value <= 15.0 and 5.0 <= candidate_value <= 15.0:
            bonus += 0.4
    return bonus


def _target_match_score(
    base_vector: Sequence[float],
    candidate_vector: Sequence[float],
    target_vector: Sequence[float],
) -> float:
    if len(target_vector) != len(base_vector):
        raise ValueError("Target vector length mismatch")
    result_vector = [
        (base_value + candidate_value) / 2
        for base_value, candidate_value in zip(base_vector, candidate_vector)
    ]
    distance = math.sqrt(
        sum((target - result) ** 2 for target, result in zip(target_vector, result_vector))
    )
    return max(0.0, 1.5 - (distance / 50.0))


def _feasibility_guard(
    base_vector: Sequence[float],
    target_vector: Sequence[float],
    target_score: float,
) -> Tuple[bool, str | None]:
    if not any(value > 0 for value in target_vector):
        return True, None

    if target_score < 0.6:
        return False, "Target alignment below threshold"

    base_top = _top_dominant(base_vector, 2)
    target_top = _top_dominant(target_vector, 2, threshold=0.0)
    if not target_top:
        return True, None

    for left, right in CLASH_PAIRS:
        if (_contains_pair(base_top, target_top, left, right)) or (
            _contains_pair(base_top, target_top, right, left)
        ):
            return False, "Dominant accords clash with target"
    return True, None


def _contains_pair(
    source: Sequence[str],
    target: Sequence[str],
    left: Iterable[str],
    right: Iterable[str],
) -> bool:
    return any(item in left for item in source) and any(item in right for item in target)


def _top_dominant(
    vector: Sequence[float],
    limit: int,
    threshold: float = 5.0,
) -> List[str]:
    ranked = sorted(
        (
            (value, ACCORDS[index])
            for index, value in enumerate(vector)
            if value > threshold
        ),
        key=lambda pair: pair[0],
        reverse=True,
    )
    return [name for _, name in ranked[:limit]]


def _spray_order(base: PerfumeVector, candidate: PerfumeVector) -> List[str]:
    if base.persistence_score >= candidate.persistence_score:
        first, second = base, candidate
    else:
        first, second = candidate, base
    return [
        f"{first.perfume_name} ({first.perfume_id})",
        f"{second.perfume_name} ({second.perfume_id})",
    ]


def _result_to_candidate(result: LayeringComputationResult) -> LayeringCandidate:
    candidate = result.candidate
    # 추천 이유 텍스트를 바꾸려면 _build_analysis_string() 로직을 조정
    analysis = _build_analysis_string(result.score_breakdown)
    return LayeringCandidate(
        perfume_id=candidate.perfume_id,
        perfume_name=candidate.perfume_name,
        perfume_brand=candidate.perfume_brand,
        total_score=round(result.total_score, 3),
        feasible=result.feasible,
        feasibility_reason=result.feasibility_reason,
        spray_order=result.spray_order,
        score_breakdown=result.score_breakdown,
        clash_detected=result.clash_detected,
        analysis=analysis,
        layered_vector=result.layered_vector,
    )


def _cosine_similarity(vector_a: Sequence[float], vector_b: Sequence[float]) -> float:
    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))
    magnitude_a = math.sqrt(sum(a * a for a in vector_a))
    magnitude_b = math.sqrt(sum(b * b for b in vector_b))
    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0
    return dot_product / (magnitude_a * magnitude_b)


def _build_analysis_string(breakdown: ScoreBreakdown) -> str:
    return (
        " + ".join(
            [
                f"Base {breakdown.base:.2f}",
                f"Harmony {breakdown.harmony:.2f}",
                f"Bridge {breakdown.bridge:.2f}",
                f"Penalty {breakdown.penalty:.2f}",
                f"Target {breakdown.target:.2f}",
            ]
        )
    )
