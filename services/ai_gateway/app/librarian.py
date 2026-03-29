from __future__ import annotations

from typing import Any

from .repository import load_curriculum
from .retrieval import SourceProvider, SourceResult, StaticSourceProvider
from .schemas import (
    AuthorizedSource,
    AuthorizedSourceResource,
    LibrarianProvenance,
    LibrarianRequest,
    LibrarianResponse,
    LibrarianResult,
)

# Tiers that are never exposed by the Librarian.
BLOCKED_TIERS = {"blocked_solution_content"}

# Foundation and practice phases also block solution metadata.
PHASE_RESTRICTED_TIERS: dict[str, set[str]] = {
    "foundation": {"solution_metadata"},
    "practice": {"solution_metadata"},
}


def _curriculum_tier_ids(curriculum: dict[str, Any]) -> list[str]:
    return [tier["id"] for tier in curriculum["source_policy"]["tiers"]]


def allowed_tiers(curriculum: dict[str, Any], phase: str) -> list[str]:
    excluded = BLOCKED_TIERS | PHASE_RESTRICTED_TIERS.get(phase, set())
    return [tier_id for tier_id in _curriculum_tier_ids(curriculum) if tier_id not in excluded]


def build_authorized_source_index(curriculum: dict[str, Any], phase: str) -> list[AuthorizedSource]:
    allowed = set(allowed_tiers(curriculum, phase))
    resources_by_tier: dict[str, list[AuthorizedSourceResource]] = {}

    for resource in curriculum.get("recommended_resources", []):
        tier = resource.get("tier")
        if tier not in allowed:
            continue
        resources_by_tier.setdefault(tier, []).append(
            AuthorizedSourceResource(
                label=resource["label"],
                url=resource.get("url"),
            )
        )

    index: list[AuthorizedSource] = []
    for tier in curriculum["source_policy"]["tiers"]:
        tier_id = tier["id"]
        if tier_id not in allowed:
            continue
        index.append(
            AuthorizedSource(
                tier=tier_id,
                tier_label=tier["label"],
                allowed_usage=tier["allowed_usage"],
                confidence_level=tier["confidence_level"],
                confidence_rationale=tier["confidence_rationale"],
                resources=resources_by_tier.get(tier_id, []),
            )
        )

    return index


def _search_with_context(
    provider: SourceProvider,
    request: LibrarianRequest,
    allowed: list[str],
) -> list[SourceResult]:
    raw_results = provider.search(
        query=request.query,
        tier_filter=allowed,
        max_results=request.max_results,
    )

    search_query = request.query
    if request.module_id:
        search_query = f"{request.module_id} {search_query}"
    elif request.track_id:
        search_query = f"{request.track_id} {search_query}"

    if search_query != request.query:
        extra_results = provider.search(
            query=search_query,
            tier_filter=allowed,
            max_results=request.max_results,
        )
        seen = {(result.content, result.tier, result.source_url) for result in raw_results}
        for result in extra_results:
            key = (result.content, result.tier, result.source_url)
            if key in seen:
                continue
            raw_results.append(result)
            seen.add(key)

    raw_results.sort(key=lambda result: result.confidence, reverse=True)
    return raw_results[: request.max_results]


def _build_result_provenance(
    result: SourceResult,
    source_index: dict[str, AuthorizedSource],
) -> LibrarianProvenance:
    source = source_index[result.tier]
    return LibrarianProvenance(
        tier=result.tier,
        tier_label=source.tier_label,
        source_label=result.source_label or source.tier_label,
        source_url=result.source_url,
        allowed_usage=source.allowed_usage,
        confidence_level=source.confidence_level,
        confidence_rationale=source.confidence_rationale,
    )


def search_librarian(
    request: LibrarianRequest,
    provider: SourceProvider | None = None,
) -> LibrarianResponse:
    curriculum = load_curriculum()
    provider = provider or StaticSourceProvider()

    allowed = allowed_tiers(curriculum, request.phase)
    authorized_sources = build_authorized_source_index(curriculum, request.phase)
    source_index = {source.tier: source for source in authorized_sources}

    raw_results = _search_with_context(provider, request, allowed)

    results: list[LibrarianResult] = []
    for raw_result in raw_results:
        provenance = _build_result_provenance(raw_result, source_index)
        results.append(
            LibrarianResult(
                content=raw_result.content,
                source_url=raw_result.source_url,
                tier=raw_result.tier,
                tier_label=provenance.tier_label,
                confidence=raw_result.confidence,
                provenance=provenance,
            )
        )

    blocked = sorted(BLOCKED_TIERS | PHASE_RESTRICTED_TIERS.get(request.phase, set()))

    sources_used: list[LibrarianProvenance] = []
    seen_sources: set[tuple[str, str, str | None]] = set()
    for result in results:
        key = (result.provenance.tier, result.provenance.source_label, result.provenance.source_url)
        if key in seen_sources:
            continue
        sources_used.append(result.provenance)
        seen_sources.add(key)

    return LibrarianResponse(
        status="ok",
        query=request.query,
        results=results,
        tiers_used=sorted({result.tier for result in results}),
        blocked_tiers=blocked,
        authorized_sources=authorized_sources,
        sources_used=sources_used,
    )
