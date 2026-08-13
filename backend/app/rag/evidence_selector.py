import re
import unicodedata


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text or "")
    without_accents = "".join(
        char for char in decomposed if unicodedata.category(char) != "Mn"
    )
    return without_accents.replace("đ", "d").replace("Đ", "D").casefold()


def select_primary_evidence_source(
    evidence_ids: list[str],
    evidence_by_id: dict[str, dict],
) -> str | None:
    """Choose one PDF source for all page images in a response."""
    source_stats: dict[str, dict] = {}
    seen_evidence_ids: set[str] = set()

    for order, evidence_id in enumerate(evidence_ids):
        canonical_id = evidence_id.upper()
        if canonical_id in seen_evidence_ids:
            continue
        seen_evidence_ids.add(canonical_id)

        evidence = evidence_by_id.get(canonical_id)
        if not evidence:
            continue

        source = str(
            evidence.get("file_name") or evidence.get("source") or ""
        ).strip()
        if not source:
            continue

        try:
            score = max(float(evidence.get("score", 0.0)), 0.0)
        except (TypeError, ValueError):
            score = 0.0

        stats = source_stats.setdefault(
            source,
            {
                "total_score": 0.0,
                "evidence_count": 0,
                "best_score": 0.0,
                "first_order": order,
            },
        )
        stats["total_score"] += score
        stats["evidence_count"] += 1
        stats["best_score"] = max(stats["best_score"], score)

    if not source_stats:
        return None

    return max(
        source_stats,
        key=lambda source: (
            source_stats[source]["total_score"],
            source_stats[source]["evidence_count"],
            source_stats[source]["best_score"],
            -source_stats[source]["first_order"],
        ),
    )


def is_procedural_overview(query: str, answer: str) -> bool:
    """Return True when the user asks for a whole procedure, not one step."""
    folded_query = _fold(query)
    if re.search(r"\b(?:buoc|step)\s*\d+\b", folded_query):
        return False

    asks_for_procedure = any(
        phrase in folded_query
        for phrase in ("huong dan", "cac buoc", "cach lam", "lam sao", "how to")
    )
    folded_answer = _fold(answer)
    answer_steps = set(
        re.findall(
            r"(?:^|\n)\s*(?:buoc\s*)?(\d+)\s*[.):]",
            folded_answer,
            flags=re.MULTILINE,
        )
    )
    return asks_for_procedure and len(answer_steps) >= 2


def select_page_image_references(
    evidence_ids: list[str],
    evidence_by_id: dict[str, dict],
    primary_source: str | None,
    *,
    expand_procedure: bool = False,
) -> list[tuple[str, int]]:
    """Select unique image pages and return them in document order.

    For a procedure overview, indexed pages carrying numbered steps in the same
    section are included. This prevents an omitted LLM citation from hiding one
    of the step images.
    """
    if not primary_source:
        return []

    selected: set[tuple[str, int]] = set()

    def add_evidence(evidence: dict) -> None:
        source = str(evidence.get("file_name") or evidence.get("source") or "").strip()
        if source != primary_source:
            return
        try:
            page = int(evidence["page"])
        except (KeyError, TypeError, ValueError):
            return
        selected.add((source, page))

        if expand_procedure:
            for related_page in evidence.get("procedural_pages", []):
                try:
                    selected.add((source, int(related_page)))
                except (TypeError, ValueError):
                    continue

    for evidence_id in evidence_ids:
        evidence = evidence_by_id.get(evidence_id.upper())
        if evidence:
            add_evidence(evidence)

    return sorted(selected, key=lambda reference: (reference[0].casefold(), reference[1]))
