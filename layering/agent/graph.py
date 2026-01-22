"""Graph-based orchestration helpers for user-driven layering flows."""

from __future__ import annotations

import json
import os
import re
from typing import Any

from pydantic import BaseModel, Field

from .constants import KEYWORD_MAP, MATCH_SCORE_THRESHOLD
from .database import PerfumeRepository
from .prompts import USER_PREFERENCE_PROMPT
from .schemas import DetectedPair, DetectedPerfume, PairingAnalysis, UserQueryAnalysis
from .tools import evaluate_pair, rank_recommendations


class PreferenceSummary(BaseModel):
    keywords: list[str] = Field(default_factory=list)
    intensity: float = 0.5
    raw_text: str = ""


def _normalize_keywords(raw_keywords: Any) -> list[str]:
    if isinstance(raw_keywords, str):
        raw_items = [raw_keywords]
    elif isinstance(raw_keywords, list):
        raw_items = raw_keywords
    else:
        raw_items = []

    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        if item is None:
            continue
        text = str(item)
        parts = [chunk.strip().lower() for chunk in text.replace(";", ",").split(",") if chunk.strip()]
        for part in parts:
            if part in seen:
                continue
            seen.add(part)
            normalized.append(part)
    return normalized


def _heuristic_preferences(user_text: str) -> PreferenceSummary:
    normalized = user_text.lower()
    keywords = [key for key in KEYWORD_MAP if key in normalized]
    intensity = 0.5
    if any(token in normalized for token in ["매우", "아주", "강하게", "intense", "strong"]):
        intensity = 0.9
    elif any(token in normalized for token in ["살짝", "약하게", "soft", "light"]):
        intensity = 0.3
    return PreferenceSummary(keywords=keywords, intensity=intensity, raw_text=user_text)


def analyze_user_input(user_text: str) -> PreferenceSummary:
    """Analyze free-form user text to extract accord keywords and intensity."""

    if not user_text or not user_text.strip():
        return PreferenceSummary(raw_text=user_text or "")
    if not os.getenv("OPENAI_API_KEY"):
        return _heuristic_preferences(user_text)

    try:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI
    except ImportError:
        return _heuristic_preferences(user_text)

    prompt = ChatPromptTemplate.from_template(USER_PREFERENCE_PROMPT)
    model = ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"), temperature=0)
    chain = prompt | model | StrOutputParser()
    response = ""
    try:
        response = chain.invoke({"user_input": user_text})
        payload = json.loads(response)
    except Exception:
        try:
            start = response.find("{")
            end = response.rfind("}")
            if start != -1 and end != -1:
                payload = json.loads(response[start : end + 1])
            else:
                return _heuristic_preferences(user_text)
        except Exception:
            return _heuristic_preferences(user_text)

    raw_keywords = payload.get("keywords", []) if isinstance(payload, dict) else []
    keywords = _normalize_keywords(raw_keywords)
    keywords = [keyword for keyword in keywords if keyword in KEYWORD_MAP]
    intensity = payload.get("intensity", 0.5) if isinstance(payload, dict) else 0.5
    try:
        intensity_value = float(intensity)
    except (TypeError, ValueError):
        intensity_value = 0.5
    intensity_value = max(0.0, min(1.0, intensity_value))
    return PreferenceSummary(keywords=keywords, intensity=intensity_value, raw_text=user_text)


def _split_query_segments(user_text: str) -> list[str]:
    separators = r"(?:&|\b(?:and|with|layering)\b|랑|와|과|레이어링)"
    parts = re.split(separators, user_text, flags=re.IGNORECASE)
    return [part.strip() for part in parts if part.strip()]


def _apply_aliases(user_text: str) -> str:
    aliases = {
        "조말론": "jo malone",
        "우드세이지": "wood sage",
        "씨솔트": "sea salt",
        "시솔트": "sea salt",
    }
    normalized = user_text
    for source, target in aliases.items():
        normalized = re.sub(source, target, normalized, flags=re.IGNORECASE)
    return normalized


def analyze_user_query(
    user_text: str,
    repository: PerfumeRepository,
    preferences: PreferenceSummary | None = None,
) -> UserQueryAnalysis:
    resolved_preferences = preferences or analyze_user_input(user_text)
    normalized_text = _apply_aliases(user_text)
    segments = _split_query_segments(normalized_text)
    min_match_score = MATCH_SCORE_THRESHOLD
    detected: dict[str, DetectedPerfume] = {}
    segment_best: dict[int, DetectedPerfume] = {}

    search_inputs = segments[:] or [normalized_text]
    if normalized_text not in search_inputs:
        search_inputs.append(normalized_text)

    for index, segment in enumerate(search_inputs):
        for perfume, score, matched_text in repository.find_perfume_candidates(segment):
            current = detected.get(perfume.perfume_id)
            if current and current.match_score >= score:
                continue
            detected_perfume = DetectedPerfume(
                perfume_id=perfume.perfume_id,
                perfume_name=perfume.perfume_name,
                perfume_brand=perfume.perfume_brand,
                match_score=score,
                matched_text=matched_text,
            )
            detected[perfume.perfume_id] = detected_perfume
            if index < len(segments) and score >= min_match_score:
                current_best = segment_best.get(index)
                if current_best is None or current_best.match_score < score:
                    segment_best[index] = detected_perfume

    detected_perfumes = sorted(
        (item for item in detected.values() if item.match_score >= min_match_score),
        key=lambda item: item.match_score,
        reverse=True,
    )

    base_perfume_id = None
    candidate_perfume_id = None
    if detected_perfumes:
        base_perfume_id = detected_perfumes[0].perfume_id
        if len(detected_perfumes) > 1:
            candidate_perfume_id = detected_perfumes[1].perfume_id

    if re.search(r"가지고|있는데|보유|has|have", user_text, flags=re.IGNORECASE):
        if segment_best:
            base_perfume_id = segment_best.get(0, detected_perfumes[0]).perfume_id
        if base_perfume_id:
            full_text_candidates = repository.find_perfume_candidates(normalized_text)
            for perfume, _, _ in full_text_candidates:
                if perfume.perfume_id != base_perfume_id:
                    candidate_perfume_id = perfume.perfume_id
                    break
        if candidate_perfume_id is None and segment_best:
            last_index = max(segment_best.keys())
            candidate = segment_best.get(last_index)
            if candidate and candidate.perfume_id != base_perfume_id:
                candidate_perfume_id = candidate.perfume_id
        if candidate_perfume_id is None and detected_perfumes:
            if len(detected_perfumes) > 1:
                candidate_perfume_id = detected_perfumes[1].perfume_id

    pairing_analysis = None
    detected_pair = None
    if base_perfume_id and candidate_perfume_id:
        result = evaluate_pair(
            base_perfume_id,
            candidate_perfume_id,
            resolved_preferences.keywords,
            repository,
        )
        detected_pair = DetectedPair(
            base_perfume_id=base_perfume_id,
            candidate_perfume_id=candidate_perfume_id,
        )
        pairing_analysis = PairingAnalysis(
            base_perfume_id=base_perfume_id,
            candidate_perfume_id=candidate_perfume_id,
            result=result,
        )

    return UserQueryAnalysis(
        raw_text=user_text,
        detected_perfumes=detected_perfumes,
        detected_pair=detected_pair,
        pairing_analysis=pairing_analysis,
    )


def preview_layering_paths(
    base_perfume_id: str,
    user_text: str,
    repository: PerfumeRepository,
) -> dict[str, Any]:
    """Analyze user input then fetch recommendations for graph previews."""

    preferences = analyze_user_input(user_text)
    keywords = preferences.keywords
    if preferences.intensity >= 0.85:
        keywords = keywords + keywords
    recommendations, _ = rank_recommendations(base_perfume_id, keywords, repository)
    return {
        "preferences": preferences.model_dump(),
        "recommendations": recommendations,
    }
