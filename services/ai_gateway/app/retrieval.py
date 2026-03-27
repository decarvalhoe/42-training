"""Abstract retrieval layer with SourceProvider interface.

This module defines the contract for retrieving curriculum-related content
from different source tiers, respecting the source-governance policy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel, Field

from .repository import load_curriculum


class SourceResult(BaseModel):
    """A single result returned by a source provider."""

    content: str
    source_url: str | None = None
    tier: str = Field(description="Source tier id from the source policy (e.g. official_42, community_docs)")
    confidence: float = Field(ge=0.0, le=1.0, description="Relevance confidence between 0 and 1")


class SourceProvider(ABC):
    """Abstract interface for retrieval backends.

    Any retrieval implementation (static, vector DB, API-based) must
    implement this interface so the ai_gateway can swap backends without
    changing the mentor orchestration logic.
    """

    @abstractmethod
    def search(
        self,
        query: str,
        tier_filter: list[str] | None = None,
        max_results: int = 5,
    ) -> list[SourceResult]:
        """Search for relevant content.

        Args:
            query: Free-text search query.
            tier_filter: If provided, only return results from these tiers.
            max_results: Maximum number of results to return.

        Returns:
            List of SourceResult ordered by descending confidence.
        """


class StaticSourceProvider(SourceProvider):
    """SourceProvider backed by the static curriculum JSON.

    Performs simple keyword matching against tracks, modules, skills,
    and recommended resources. Suitable for the MVP phase before a
    proper vector store is introduced.
    """

    def __init__(self) -> None:
        self._curriculum = load_curriculum()

    def search(
        self,
        query: str,
        tier_filter: list[str] | None = None,
        max_results: int = 5,
    ) -> list[SourceResult]:
        results: list[SourceResult] = []
        query_lower = query.lower()

        # Search tracks and modules
        for track in self._curriculum.get("tracks", []):
            self._match_track(track, query_lower, results)

        # Search recommended resources
        for resource in self._curriculum.get("recommended_resources", []):
            self._match_resource(resource, query_lower, results)

        # Apply tier filter
        if tier_filter is not None:
            results = [r for r in results if r.tier in tier_filter]

        # Sort by confidence descending, truncate
        results.sort(key=lambda r: r.confidence, reverse=True)
        return results[:max_results]

    def _match_track(self, track: dict, query_lower: str, results: list[SourceResult]) -> None:
        track_text = f"{track.get('title', '')} {track.get('summary', '')}".lower()
        if query_lower in track_text:
            results.append(
                SourceResult(
                    content=f"Track: {track['title']} — {track.get('summary', '')}",
                    tier="official_42",
                    confidence=0.7,
                )
            )

        for module in track.get("modules", []):
            module_text = f"{module.get('title', '')} {module.get('deliverable', '')}".lower()
            skills_text = " ".join(module.get("skills", [])).lower()
            combined = f"{module_text} {skills_text}"

            if query_lower in combined:
                results.append(
                    SourceResult(
                        content=f"Module: {module['title']} (track: {track['id']}, phase: {module.get('phase', 'unknown')}) — Skills: {', '.join(module.get('skills', []))}",
                        tier="official_42",
                        confidence=0.8,
                    )
                )

    def _match_resource(self, resource: dict, query_lower: str, results: list[SourceResult]) -> None:
        label = resource.get("label", "").lower()
        if query_lower in label:
            results.append(
                SourceResult(
                    content=f"Resource: {resource['label']}",
                    source_url=resource.get("url"),
                    tier=resource.get("tier", "community_docs"),
                    confidence=0.6,
                )
            )
