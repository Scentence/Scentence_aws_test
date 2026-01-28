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


def test_analyze_user_input_intensity_levels(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    strong = analyze_user_input("진하게 레이어링 하고 싶어")
    soft = analyze_user_input("은은하게 바꾸고 싶어")

    assert strong.intensity >= 0.8
    assert soft.intensity <= 0.4


def test_analyze_user_input_korean_keywords(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cool_summary = analyze_user_input("ck one이 좀 더 차가운 향이 되게")
    floral_summary = analyze_user_input("ck one에서 좀 더 플로럴하게")
    spicy_summary = analyze_user_input("ck one에서 스파이시하게")

    assert "차가운" in cool_summary.keywords
    assert "플로럴" in floral_summary.keywords
    assert "스파이시" in spicy_summary.keywords


def test_analyze_user_input_prefers_longer_matches(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    summary = analyze_user_input("green tea layered with ck one")

    assert "green tea" in summary.keywords
    assert "green" not in summary.keywords


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


def test_analyze_user_query_uses_context_for_followup():
    repo = PerfumeRepository()
    analysis = analyze_user_query(
        "방금 추천한 향수랑 ck one이랑 레이어링하면 어때?",
        repo,
        context_recommended_perfume_id="9300",
    )

    assert analysis.detected_pair is not None
    assert analysis.detected_pair.base_perfume_id == "8701"
    assert analysis.detected_pair.candidate_perfume_id == "9300"


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


def test_korean_alias_un_jardin_sur_le_toit_detected():
    repo = PerfumeRepository()
    analysis = analyze_user_query("운 자르뎅 수르뜨와와 레이어링하기 좋은 향수 추천해줘", repo)

    assert any(
        "un jardin sur le toit" in perfume.perfume_name.lower()
        for perfume in analysis.detected_perfumes
    )


def test_korean_alias_dior_sauvage_detected():
    repo = PerfumeRepository()
    analysis = analyze_user_query("디올 소바쥬를 갖고 있는데 좀 더 우디한 느낌으로", repo)

    assert any(
        "sauvage" in perfume.perfume_name.lower()
        and "dior" in perfume.perfume_brand.lower()
        for perfume in analysis.detected_perfumes
    )


def test_korean_alias_wood_sage_sea_salt_detected():
    repo = PerfumeRepository()
    analysis = analyze_user_query("조말론 우드 세이지 시솔트를 기반으로", repo)

    assert any(
        "wood sage" in perfume.perfume_name.lower()
        for perfume in analysis.detected_perfumes
    )


def test_brand_layering_request_returns_brand_pick():
    repo = PerfumeRepository()
    analysis = analyze_user_query("조말론 향수중에 어디에나 레이어링하기 좋은 향수 있어?", repo)

    assert analysis.brand_name is not None
    assert analysis.brand_best_perfume is not None


def test_info_request_returns_perfume_info_from_query():
    repo = PerfumeRepository()
    analysis = analyze_user_query("CK One 정보 알려줘", repo)

    assert analysis.recommended_perfume_info is not None
