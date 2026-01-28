"""Graph-based orchestration helpers for user-driven layering flows."""

from __future__ import annotations

import json
import os
from typing import Any

from pydantic import BaseModel, Field

from .constants import KEYWORD_MAP
from .database import PerfumeRepository, get_perfume_info
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


def _split_query_segments(text: str) -> list[str]:
    if not text:
        return []
    lowered = text.lower()
    separators = [" and ", "&", ",", ";"]
    segments = [lowered]
    for sep in separators:
        next_segments: list[str] = []
        for segment in segments:
            next_segments.extend(segment.split(sep))
        segments = next_segments
    cleaned = [segment.strip() for segment in segments if segment.strip()]
    return cleaned


def _heuristic_preferences(user_text: str) -> PreferenceSummary:
    normalized = user_text.lower()
    matched = [key for key in KEYWORD_MAP if key in normalized]
    keywords = []
    for key in matched:
        if any(other != key and key in other for other in matched):
            if len(key) < max(len(other) for other in matched if key in other):
                continue
        keywords.append(key)
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


def _build_detected_perfumes(
    candidates: list[tuple[Any, float, str]],
) -> list[DetectedPerfume]:
    detected: list[DetectedPerfume] = []
    seen: set[str] = set()
    for perfume, score, matched_text in candidates:
        perfume_id = perfume.perfume_id
        if perfume_id in seen:
            continue
        seen.add(perfume_id)
        detected.append(
            DetectedPerfume(
                perfume_id=perfume_id,
                perfume_name=perfume.perfume_name,
                perfume_brand=perfume.perfume_brand,
                match_score=score,
                matched_text=matched_text,
            )
        )
    return detected


def is_info_request(user_text: str) -> bool:
    normalized = user_text.lower()
    keywords = [
        "정보",
        "알려",
        "노트",
        "어코드",
        "향조",
        "구성",
        "details",
        "note",
        "accord",
    ]
    return any(token in normalized for token in keywords)


def analyze_user_query(
    user_text: str,
    repository: PerfumeRepository,
    preferences: PreferenceSummary | None = None,
    context_recommended_perfume_id: str | None = None,
) -> UserQueryAnalysis:
    if not user_text or not user_text.strip():
        return UserQueryAnalysis(raw_text=user_text or "", detected_perfumes=[])

    if preferences is None:
        preferences = _heuristic_preferences(user_text)

    if is_info_request(user_text):
        if context_recommended_perfume_id:
            info = get_perfume_info(context_recommended_perfume_id)
            return UserQueryAnalysis(
                raw_text=user_text,
                detected_perfumes=[],
                recommended_perfume_info=info,
            )
        return UserQueryAnalysis(raw_text=user_text, detected_perfumes=[])

    candidates = repository.find_perfume_candidates(user_text, limit=6)
    detected_perfumes = _build_detected_perfumes(candidates)

    detected_pair = None
    pairing_analysis = None
    if len(detected_perfumes) >= 2:
        base_candidate = detected_perfumes[0]
        candidate = detected_perfumes[1]
        detected_pair = DetectedPair(
            base_perfume_id=base_candidate.perfume_id,
            candidate_perfume_id=candidate.perfume_id,
        )
        pairing_result = evaluate_pair(
            base_candidate.perfume_id,
            candidate.perfume_id,
            preferences.keywords,
            repository,
        )
        pairing_analysis = PairingAnalysis(
            base_perfume_id=base_candidate.perfume_id,
            candidate_perfume_id=candidate.perfume_id,
            result=pairing_result,
        )

    return UserQueryAnalysis(
        raw_text=user_text,
        detected_perfumes=detected_perfumes,
        detected_pair=detected_pair,
        pairing_analysis=pairing_analysis,
    )


def suggest_perfume_options(
    user_text: str,
    repository: PerfumeRepository,
    limit: int = 5,
) -> list[str]:
    if not user_text or not user_text.strip():
        return []
    candidates = repository.find_perfume_candidates(user_text, limit=limit)
    detected = _build_detected_perfumes(candidates)
    return [f"{item.perfume_name} ({item.perfume_brand})" for item in detected]


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
