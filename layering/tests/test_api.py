from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_recommend_endpoint_returns_note_when_under_three():
    response = client.post(
        "/layering/recommend",
        json={"base_perfume_id": "P001", "keywords": ["warm"]},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total_available"] == 1
    assert payload["note"]
    assert len(payload["recommendations"]) == 1
    recommendation = payload["recommendations"][0]
    assert recommendation["feasible"] is True
    assert "Harmony" in recommendation["analysis"]


def test_recommend_endpoint_returns_404_for_unknown_base():
    response = client.post(
        "/layering/recommend",
        json={"base_perfume_id": "UNKNOWN", "keywords": []},
    )

    assert response.status_code == 404
