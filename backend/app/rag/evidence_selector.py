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
