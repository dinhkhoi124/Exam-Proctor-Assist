import os
import re
import unicodedata


PARENT_MAX_LENGTH = 1200
CHILD_MAX_LENGTH = 380
CHILD_OVERLAP = 70


def _clean_text(text: str) -> str:
    """Normalize PDF text while preserving line boundaries used as structure."""
    text = unicodedata.normalize("NFC", text or "")
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line).strip()


def _find_boundary(text: str, start: int, proposed_end: int) -> int:
    """Find a readable split point without allowing very small chunks."""
    minimum_end = start + int((proposed_end - start) * 0.6)
    window = text[minimum_end:proposed_end]
    for marker in ("\n", ". ", "; ", ": ", " "):
        position = window.rfind(marker)
        if position != -1:
            return minimum_end + position + len(marker)
    return proposed_end


def _split_text(text: str, max_length: int, overlap: int = 0) -> list[str]:
    """Split on readable boundaries and keep a bounded child overlap."""
    if len(text) <= max_length:
        return [text] if text else []

    chunks = []
    start = 0
    while start < len(text):
        proposed_end = min(start + max_length, len(text))
        end = (
            _find_boundary(text, start, proposed_end)
            if proposed_end < len(text)
            else proposed_end
        )
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break

        next_start = max(end - overlap, start + 1)
        while next_start < end and next_start > 0 and not text[next_start - 1].isspace():
            next_start += 1
        start = min(next_start, end)

    return chunks


def _page_heading(text: str) -> str:
    """Extract a conservative heading from the first lines of a PDF page."""
    for line in text.splitlines()[:6]:
        candidate = re.sub(r"\s+", " ", line).strip(" -•\t")
        if not candidate or len(candidate) > 180:
            continue
        letters = [char for char in candidate if char.isalpha()]
        uppercase_ratio = (
            sum(char.isupper() for char in letters) / len(letters)
            if letters
            else 0.0
        )
        if (
            uppercase_ratio >= 0.55
            or re.match(
                r"^(?:bước|lưu ý|chú ý|hướng dẫn|mục|phần|điều|trường hợp|\d+[.)])\b",
                candidate,
                flags=re.IGNORECASE,
            )
        ):
            return candidate

    first_line = text.splitlines()[0] if text.splitlines() else ""
    return re.sub(r"\s+", " ", first_line)[:180].strip()


def semantic_chunk(
    documents,
    parent_max_length: int = PARENT_MAX_LENGTH,
    child_max_length: int = CHILD_MAX_LENGTH,
    child_overlap: int = CHILD_OVERLAP,
):
    """Create child chunks for retrieval and page-bounded parents for the LLM.

    Keeping parents inside one PDF page preserves exact page citations while child
    retrieval provides enough granularity for BM25 and dense search.
    """
    chunks = []

    for doc in documents:
        text = _clean_text(doc.get("content", ""))
        if not text:
            continue

        page = int(doc.get("page", 0))
        source = doc.get("source", "unknown.pdf")
        document_title = os.path.splitext(source)[0].strip()
        heading = _page_heading(text)

        parents = _split_text(text, max_length=parent_max_length)
        for parent_index, parent_text in enumerate(parents):
            parent_id = f"{source}::page-{page}::parent-{parent_index}"
            children = _split_text(
                parent_text,
                max_length=child_max_length,
                overlap=child_overlap,
            )

            for child_index, child_text in enumerate(children):
                section_parts = [document_title]
                if heading and heading.casefold() != document_title.casefold():
                    section_parts.append(heading)
                section_path = " > ".join(
                    part for part in section_parts if part
                )
                retrieval_text = f"{section_path}\n{child_text}".strip()
                chunks.append(
                    {
                        "text": child_text,
                        "retrieval_text": retrieval_text,
                        "display_text": parent_text,
                        "parent_text": parent_text,
                        "page": page,
                        "source": source,
                        "document_title": document_title,
                        "heading": heading,
                        "section_path": section_path,
                        "parent_id": parent_id,
                        "child_id": f"{parent_id}::child-{child_index}",
                    }
                )

    return chunks
