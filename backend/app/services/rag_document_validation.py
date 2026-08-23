"""Pure validation helpers for RAG document updates."""

from __future__ import annotations

from collections.abc import Iterable


class UnindexableDocumentError(ValueError):
    def __init__(self, sources: list[str]):
        self.sources = sources
        super().__init__(
            "PDFs produced no usable RAG chunks: "
            f"{', '.join(sources)}"
        )


def find_case_variant_collisions(
    requested_names: Iterable[str],
    existing_names: Iterable[str],
) -> list[tuple[str, str]]:
    """Return names that only differ from an existing document by case."""
    existing_by_folded: dict[str, str] = {}
    for existing_name in existing_names:
        existing_by_folded.setdefault(existing_name.casefold(), existing_name)

    collisions = []
    for requested_name in requested_names:
        existing_name = existing_by_folded.get(requested_name.casefold())
        if existing_name is not None and existing_name != requested_name:
            collisions.append((requested_name, existing_name))
    return collisions


def find_unindexed_sources(
    required_sources: Iterable[str],
    metadata: Iterable[dict],
) -> list[str]:
    """Return uploaded PDFs that produced no usable RAG chunks."""
    indexed_sources = {
        str(item.get("source")).casefold()
        for item in metadata
        if item.get("source")
    }
    return [
        source
        for source in required_sources
        if source.casefold() not in indexed_sources
    ]
