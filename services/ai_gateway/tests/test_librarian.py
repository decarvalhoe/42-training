"""Tests for the Librarian endpoint — filtered resource search."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

ENDPOINT = "/api/v1/librarian/search"


def test_librarian_basic_search() -> None:
    response = client.post(ENDPOINT, json={"query": "shell"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["query"] == "shell"
    assert isinstance(data["results"], list)
    assert len(data["results"]) > 0


def test_librarian_results_have_expected_fields() -> None:
    response = client.post(ENDPOINT, json={"query": "shell"})
    data = response.json()
    assert "authorized_sources" in data
    assert "sources_used" in data
    for result in data["results"]:
        assert "content" in result
        assert "tier" in result
        assert "tier_label" in result
        assert "confidence" in result
        assert "provenance" in result
        assert 0.0 <= result["confidence"] <= 1.0


def test_librarian_never_returns_blocked_tiers() -> None:
    """Blocked solution content must never appear in Librarian results."""
    response = client.post(ENDPOINT, json={"query": "shell", "max_results": 20})
    data = response.json()
    for result in data["results"]:
        assert result["tier"] != "blocked_solution_content"
    assert "blocked_solution_content" in data["blocked_tiers"]
    assert all(source["tier"] != "blocked_solution_content" for source in data["authorized_sources"])


def test_librarian_foundation_blocks_solution_metadata() -> None:
    """In foundation phase, solution_metadata tier is also blocked."""
    response = client.post(ENDPOINT, json={"query": "shell", "phase": "foundation", "max_results": 20})
    data = response.json()
    for result in data["results"]:
        assert result["tier"] != "solution_metadata"
    assert "solution_metadata" in data["blocked_tiers"]
    assert all(source["tier"] != "solution_metadata" for source in data["authorized_sources"])


def test_librarian_advanced_allows_solution_metadata() -> None:
    """In advanced phase, solution_metadata is allowed."""
    response = client.post(ENDPOINT, json={"query": "shell", "phase": "advanced"})
    data = response.json()
    assert "solution_metadata" not in data["blocked_tiers"]
    assert any(source["tier"] == "solution_metadata" for source in data["authorized_sources"])


def test_librarian_with_track_context() -> None:
    response = client.post(ENDPOINT, json={"query": "memory", "track_id": "c"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_librarian_with_module_context() -> None:
    response = client.post(ENDPOINT, json={"query": "malloc", "track_id": "c", "module_id": "c-memory"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) > 0


def test_librarian_max_results_respected() -> None:
    response = client.post(ENDPOINT, json={"query": "shell", "max_results": 2})
    data = response.json()
    assert len(data["results"]) <= 2


def test_librarian_no_match_returns_empty() -> None:
    response = client.post(ENDPOINT, json={"query": "xyznonexistent999"})
    data = response.json()
    assert data["results"] == []
    assert data["tiers_used"] == []


def test_librarian_results_sorted_by_confidence() -> None:
    response = client.post(ENDPOINT, json={"query": "shell"})
    data = response.json()
    results = data["results"]
    if len(results) > 1:
        for i in range(len(results) - 1):
            assert results[i]["confidence"] >= results[i + 1]["confidence"]


def test_librarian_tiers_used_reflects_results() -> None:
    response = client.post(ENDPOINT, json={"query": "norminette"})
    data = response.json()
    result_tiers = {r["tier"] for r in data["results"]}
    assert result_tiers == set(data["tiers_used"])
    assert {item["tier"] for item in data["sources_used"]} == result_tiers


def test_librarian_query_too_short() -> None:
    response = client.post(ENDPOINT, json={"query": "x"})
    assert response.status_code == 422


def test_librarian_resource_includes_url() -> None:
    """Resources like norminette should include source_url."""
    response = client.post(ENDPOINT, json={"query": "norminette"})
    data = response.json()
    assert any(r["source_url"] is not None for r in data["results"])


def test_librarian_result_includes_explicit_provenance() -> None:
    response = client.post(ENDPOINT, json={"query": "norminette"})
    data = response.json()
    result = next(item for item in data["results"] if item["source_url"] is not None)
    provenance = result["provenance"]
    assert provenance["tier"] == result["tier"]
    assert provenance["tier_label"] == result["tier_label"]
    assert provenance["source_label"]
    assert provenance["allowed_usage"]
    assert provenance["confidence_level"]
    assert provenance["confidence_rationale"]


def test_librarian_authorized_sources_are_built_from_source_policy() -> None:
    response = client.post(ENDPOINT, json={"query": "shell"})
    data = response.json()
    official = next(item for item in data["authorized_sources"] if item["tier"] == "official_42")
    assert official["tier_label"] == "Official 42 sources"
    assert official["allowed_usage"] == "ground_truth"
    assert official["confidence_level"] == "high"


def test_librarian_authorized_sources_include_recommended_resources() -> None:
    response = client.post(ENDPOINT, json={"query": "shell"})
    data = response.json()
    testers = next(item for item in data["authorized_sources"] if item["tier"] == "testers_and_tooling")
    labels = {resource["label"] for resource in testers["resources"]}
    assert "norminette" in labels
