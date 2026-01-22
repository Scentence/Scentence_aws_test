from agent.database import PerfumeRepository
from agent.graph import (
    _normalize_keywords,
    _split_query_segments,
    analyze_user_input,
    analyze_user_query,
)


def test_analyze_user_input_heuristics(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    summary = analyze_user_input("warm and sweet")

    assert "warm" in summary.keywords
    assert "sweet" in summary.keywords
    assert 0.0 <= summary.intensity <= 1.0


def test_normalize_keywords_splits_delimiters():
    assert _normalize_keywords("citrus; warm, sweet") == ["citrus", "warm", "sweet"]
    assert _normalize_keywords(["citrus; warm", "sweet"]) == ["citrus", "warm", "sweet"]
    assert _normalize_keywords("citrus, , ;") == ["citrus"]
    assert _normalize_keywords("warm, warm") == ["warm"]
    assert _normalize_keywords("Warm, warm") == ["warm"]
    assert _normalize_keywords(None) == []
    assert _normalize_keywords([]) == []


def test_analyze_user_query_detects_pair():
    repo = PerfumeRepository()
    query = "I have CK One. Would Jo Malone Wood Sage & Sea Salt layer well?"

    analysis = analyze_user_query(query, repo)

    assert analysis.detected_pair is not None
    assert analysis.detected_pair.base_perfume_id == "8701"
    assert analysis.detected_pair.candidate_perfume_id == "9300"
    assert analysis.pairing_analysis is not None


def test_split_query_segments_respects_words():
    segments = _split_query_segments("sandalwood and citrus")
    assert segments == ["sandalwood", "citrus"]


def test_analyze_user_query_filters_low_confidence():
    repo = PerfumeRepository()
    analysis = analyze_user_query("completely unrelated text", repo)

    assert analysis.detected_perfumes == []
    assert analysis.detected_pair is None


def test_short_abbreviation_not_matched():
    repo = PerfumeRepository()
    analysis = analyze_user_query("ck", repo)

    assert analysis.detected_perfumes == []
