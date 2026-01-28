from fastapi.testclient import TestClient

from main import app, get_repository


client = TestClient(app)


def test_recommend_endpoint_returns_note_when_under_three():
    base_perfume_id = next(iter(get_repository().all_candidates())).perfume_id
    response = client.post(
        "/layering/recommend",
        json={"base_perfume_id": base_perfume_id, "keywords": ["warm"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["base_perfume_id"] == base_perfume_id
    assert payload["total_available"] >= len(payload["recommendations"])
    assert len(payload["recommendations"]) <= 3
    if payload["total_available"] < 3:
        assert payload["note"]
    else:
        assert payload["note"] is None
    if payload["recommendations"]:
        recommendation = payload["recommendations"][0]
        assert recommendation["feasible"] is True
        assert recommendation["analysis"]
        assert len(recommendation["spray_order"]) == 2


def test_recommend_endpoint_returns_404_for_unknown_base():
    response = client.post(
        "/layering/recommend",
        json={"base_perfume_id": "UNKNOWN", "keywords": []},
    )

    assert response.status_code == 404


def test_analyze_endpoint_returns_recommendation():
    response = client.post(
        "/layering/analyze",
        json={
            "user_text": "I have CK One. Would Jo Malone Wood Sage & Sea Salt layer well?",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["raw_text"]
    assert payload["keywords"] is not None
    assert payload["detected_perfumes"]
    assert payload["recommendation"]
    assert len(payload["recommendation"]["layered_vector"]) == 21


def test_analyze_endpoint_handles_base_only():
    response = client.post(
        "/layering/analyze",
        json={"user_text": "Tell me about CK One"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["base_perfume_id"]
    assert payload["recommendation"]


def test_analyze_endpoint_handles_no_match():
    response = client.post(
        "/layering/analyze",
        json={"user_text": "completely unrelated text"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["recommendation"] is None
    assert payload["note"]
    assert payload["clarification_prompt"]
    assert isinstance(payload["clarification_options"], list)


def test_analyze_endpoint_handles_empty_text():
    response = client.post(
        "/layering/analyze",
        json={"user_text": "   "},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["detected_perfumes"] == []
    assert payload["recommendation"] is None
    assert payload["note"]
