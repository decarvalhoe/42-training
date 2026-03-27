"""Tests for provenance tracking in mentor responses (#33).

Every mentor response must include:
- sources_used: list of sources consulted (tier, label, optional url)
- confidence_level: high/medium/low derived from source tiers
- reasoning_trace: explanation of how the response was constructed
"""

from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ENDPOINT = "/api/v1/mentor/respond"

MOCK_LLM_RESPONSE = {
    "observation": "Tu travailles sur les bases shell.",
    "question": "Quelle commande as-tu essayee en premier?",
    "hint": "Regarde la page man de cp.",
    "next_action": "Essaie cp avec un seul fichier d'abord.",
}

BASE_PAYLOAD = {
    "track_id": "shell",
    "module_id": "shell-basics",
    "question": "Je bloque sur cp",
    "pace_mode": "normal",
    "phase": "foundation",
}


# --- Provenance always present ---


@patch("app.main.get_mentor_response", return_value=MOCK_LLM_RESPONSE)
def test_provenance_fields_present_with_llm(mock_llm) -> None:
    response = client.post(ENDPOINT, json=BASE_PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    assert "sources_used" in data
    assert "confidence_level" in data
    assert "reasoning_trace" in data


@patch("app.main.get_mentor_response", side_effect=RuntimeError("No API key"))
def test_provenance_fields_present_with_fallback(mock_llm) -> None:
    response = client.post(ENDPOINT, json=BASE_PAYLOAD)
    assert response.status_code == 200
    data = response.json()
    assert "sources_used" in data
    assert "confidence_level" in data
    assert "reasoning_trace" in data


# --- sources_used ---


@patch("app.main.get_mentor_response", return_value=MOCK_LLM_RESPONSE)
def test_sources_used_is_nonempty_list(mock_llm) -> None:
    response = client.post(ENDPOINT, json=BASE_PAYLOAD)
    data = response.json()
    assert isinstance(data["sources_used"], list)
    assert len(data["sources_used"]) > 0


@patch("app.main.get_mentor_response", return_value=MOCK_LLM_RESPONSE)
def test_sources_used_contains_curriculum(mock_llm) -> None:
    """The curriculum JSON is always consulted."""
    response = client.post(ENDPOINT, json=BASE_PAYLOAD)
    data = response.json()
    tiers = [s["tier"] for s in data["sources_used"]]
    assert "official_42" in tiers


@patch("app.main.get_mentor_response", return_value=MOCK_LLM_RESPONSE)
def test_sources_used_includes_module_when_provided(mock_llm) -> None:
    response = client.post(ENDPOINT, json=BASE_PAYLOAD)
    data = response.json()
    labels = [s["label"] for s in data["sources_used"]]
    assert any("Navigation and files" in label for label in labels)


@patch("app.main.get_mentor_response", return_value=MOCK_LLM_RESPONSE)
def test_sources_used_no_module_without_module_id(mock_llm) -> None:
    payload = {**BASE_PAYLOAD, "module_id": None}
    response = client.post(ENDPOINT, json=payload)
    data = response.json()
    labels = [s["label"] for s in data["sources_used"]]
    assert not any("Module:" in label for label in labels)


@patch("app.main.get_mentor_response", return_value=MOCK_LLM_RESPONSE)
def test_sources_used_have_valid_structure(mock_llm) -> None:
    response = client.post(ENDPOINT, json=BASE_PAYLOAD)
    data = response.json()
    for source in data["sources_used"]:
        assert "tier" in source
        assert "label" in source
        assert isinstance(source["tier"], str)
        assert isinstance(source["label"], str)


@patch("app.main.get_mentor_response", return_value=MOCK_LLM_RESPONSE)
def test_sources_used_includes_recommended_resources(mock_llm) -> None:
    """Recommended resources from curriculum should appear in sources."""
    response = client.post(ENDPOINT, json=BASE_PAYLOAD)
    data = response.json()
    urls = [s.get("url") for s in data["sources_used"] if s.get("url")]
    assert len(urls) > 0


# --- confidence_level ---


@patch("app.main.get_mentor_response", return_value=MOCK_LLM_RESPONSE)
def test_confidence_high_with_llm(mock_llm) -> None:
    """LLM path with official_42 data should yield high confidence."""
    response = client.post(ENDPOINT, json=BASE_PAYLOAD)
    data = response.json()
    assert data["confidence_level"] == "high"


@patch("app.main.get_mentor_response", side_effect=RuntimeError("No API key"))
def test_confidence_medium_with_fallback(mock_llm) -> None:
    """Fallback path should yield medium confidence (still uses curriculum)."""
    response = client.post(ENDPOINT, json=BASE_PAYLOAD)
    data = response.json()
    assert data["confidence_level"] == "medium"


@patch("app.main.get_mentor_response", return_value=MOCK_LLM_RESPONSE)
def test_confidence_is_valid_value(mock_llm) -> None:
    response = client.post(ENDPOINT, json=BASE_PAYLOAD)
    data = response.json()
    assert data["confidence_level"] in ("high", "medium", "low")


# --- reasoning_trace ---


@patch("app.main.get_mentor_response", return_value=MOCK_LLM_RESPONSE)
def test_reasoning_trace_nonempty_with_llm(mock_llm) -> None:
    response = client.post(ENDPOINT, json=BASE_PAYLOAD)
    data = response.json()
    assert len(data["reasoning_trace"]) > 0


@patch("app.main.get_mentor_response", return_value=MOCK_LLM_RESPONSE)
def test_reasoning_trace_mentions_llm(mock_llm) -> None:
    response = client.post(ENDPOINT, json=BASE_PAYLOAD)
    data = response.json()
    assert "LLM" in data["reasoning_trace"] or "llm" in data["reasoning_trace"]


@patch("app.main.get_mentor_response", side_effect=RuntimeError("No API key"))
def test_reasoning_trace_mentions_fallback(mock_llm) -> None:
    response = client.post(ENDPOINT, json=BASE_PAYLOAD)
    data = response.json()
    trace_lower = data["reasoning_trace"].lower()
    assert "fallback" in trace_lower or "static" in trace_lower


@patch("app.main.get_mentor_response", return_value=MOCK_LLM_RESPONSE)
def test_reasoning_trace_mentions_track(mock_llm) -> None:
    response = client.post(ENDPOINT, json=BASE_PAYLOAD)
    data = response.json()
    assert "shell" in data["reasoning_trace"]


@patch("app.main.get_mentor_response", return_value=MOCK_LLM_RESPONSE)
def test_reasoning_trace_mentions_module_when_provided(mock_llm) -> None:
    response = client.post(ENDPOINT, json=BASE_PAYLOAD)
    data = response.json()
    assert "shell-basics" in data["reasoning_trace"]


@patch("app.main.get_mentor_response", return_value=MOCK_LLM_RESPONSE)
def test_provenance_with_c_track(mock_llm) -> None:
    """Provenance works across different tracks."""
    payload = {
        "track_id": "c",
        "module_id": "c-memory",
        "question": "Je ne comprends pas malloc",
        "phase": "foundation",
    }
    response = client.post(ENDPOINT, json=payload)
    data = response.json()
    assert data["confidence_level"] in ("high", "medium", "low")
    assert len(data["sources_used"]) > 0
    assert "c" in data["reasoning_trace"]
