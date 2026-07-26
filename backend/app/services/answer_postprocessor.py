import re


_EVIDENCE_CITATION_PATTERN = re.compile(
    r"\[\s*(?:(?:sử dụng|nguồn|tham khảo|evidence)\s*:?\s*)?E\s*(\d+)\s*\]",
    flags=re.IGNORECASE,
)
_CANONICAL_EVIDENCE_PATTERN = re.compile(r"\[E(\d+)\]", flags=re.IGNORECASE)


def normalize_evidence_citations(answer: str) -> str:
    """Convert common model citation variants to the canonical ``[E1]`` form."""
    return _EVIDENCE_CITATION_PATTERN.sub(
        lambda match: f"[E{match.group(1)}]",
        answer,
    )


def extract_evidence_ids(answer: str) -> list[str]:
    """Return evidence IDs in their order of appearance."""
    normalized = normalize_evidence_citations(answer)
    return [
        f"E{number}"
        for number in _CANONICAL_EVIDENCE_PATTERN.findall(normalized)
    ]


def strip_evidence_citations(answer: str) -> str:
    """Remove citations from display text without leaving untidy whitespace."""
    normalized = normalize_evidence_citations(answer)
    cleaned = _CANONICAL_EVIDENCE_PATTERN.sub("", normalized)
    cleaned = re.sub(r"[ \t]+(?=\n|$)", "", cleaned)
    cleaned = re.sub(r" {2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;:!?])", r"\1", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
