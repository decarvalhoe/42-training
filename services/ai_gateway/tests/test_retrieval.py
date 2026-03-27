"""Tests for the abstract retrieval layer and StaticSourceProvider."""

from app.retrieval import SourceProvider, SourceResult, StaticSourceProvider


def test_source_result_model() -> None:
    result = SourceResult(content="test", tier="official_42", confidence=0.9)
    assert result.content == "test"
    assert result.source_url is None
    assert result.tier == "official_42"
    assert result.confidence == 0.9


def test_source_result_with_url() -> None:
    result = SourceResult(
        content="test",
        source_url="https://example.com",
        tier="community_docs",
        confidence=0.5,
    )
    assert result.source_url == "https://example.com"


def test_static_provider_is_source_provider() -> None:
    provider = StaticSourceProvider()
    assert isinstance(provider, SourceProvider)


def test_static_search_shell_basics() -> None:
    provider = StaticSourceProvider()
    results = provider.search("navigation")
    assert len(results) > 0
    assert all(isinstance(r, SourceResult) for r in results)
    assert all(0.0 <= r.confidence <= 1.0 for r in results)


def test_static_search_by_skill() -> None:
    provider = StaticSourceProvider()
    results = provider.search("malloc")
    assert len(results) > 0
    # malloc is in c-memory module
    assert any("memory" in r.content.lower() or "malloc" in r.content.lower() for r in results)


def test_static_search_resource() -> None:
    provider = StaticSourceProvider()
    results = provider.search("norminette")
    assert len(results) > 0
    assert any(r.source_url is not None for r in results)


def test_static_search_tier_filter() -> None:
    provider = StaticSourceProvider()
    # norminette is a testers_and_tooling resource
    results_all = provider.search("norminette")
    results_filtered = provider.search("norminette", tier_filter=["official_42"])
    assert len(results_filtered) <= len(results_all)
    assert all(r.tier == "official_42" for r in results_filtered)


def test_static_search_max_results() -> None:
    provider = StaticSourceProvider()
    results = provider.search("shell", max_results=2)
    assert len(results) <= 2


def test_static_search_no_match() -> None:
    provider = StaticSourceProvider()
    results = provider.search("xyznonexistent999")
    assert results == []


def test_static_search_results_sorted_by_confidence() -> None:
    provider = StaticSourceProvider()
    results = provider.search("shell")
    if len(results) > 1:
        for i in range(len(results) - 1):
            assert results[i].confidence >= results[i + 1].confidence
