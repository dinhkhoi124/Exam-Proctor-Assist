import math
import os
import re
import unicodedata
from difflib import SequenceMatcher

from app.core.config import VECTOR_STORE_DIR
from app.rag.embedder import BM25Retriever, VectorStore
from app.rag.temporal_resolver import build_temporal_catalog, resolve_temporal_evidence


DENSE_TOP_K = 30
BM25_TOP_K = 30
RRF_K = 60
DENSE_WEIGHT = 0.5
BM25_WEIGHT = 0.5
FUSION_TOP_K = 15
FINAL_CONTEXT_TOP_K = 5
MIN_DENSE_SCORE = float(
    os.getenv("RAG_MIN_DENSE_SCORE", "0.83")
)
MIN_BM25_SCORE = float(os.getenv("RAG_MIN_BM25_SCORE", "20.0"))
MAX_CONTEXT_CHARACTERS = 6500
TEMPORAL_RESOLVER_ENABLED = os.getenv("RAG_TEMPORAL_RESOLVER_ENABLED", "true").lower() in {
    "1", "true", "yes",
}

_resources = None
_temporal_catalog = {}
_procedural_page_catalog: dict[tuple[str, str, int], tuple[int, ...]] = {}
_DOMAIN_TERMS = {
    "eos", "eosclient", "pea", "pealogin", "e360",
    "usb", "fu-exam", "wifi", "wi-fi",
}
_STOPWORDS = {
    "các", "có", "của", "cho", "được", "giám", "thị", "hướng", "dẫn",
    "khi", "là", "làm", "một", "này", "phải", "sinh", "thì", "trong",
    "trường", "và", "với",
}


def _procedure_section_key(section: str) -> str:
    """Collapse step headings to their stable parent section."""
    parts = [part.strip() for part in str(section or "").split(" > ") if part.strip()]
    for index, part in enumerate(parts):
        if re.match(r"^\s*(?:buoc|step)\s*\d+\b", _fold(part)):
            # A step heading can itself contain the ">" character. Drop it and
            # every fragment after it, retaining only the stable parent path.
            parts = parts[:index]
            break

    normalized_parts = []
    for part in parts:
        normalized = _fold(part)
        if not normalized:
            continue
        if normalized_parts and SequenceMatcher(
            None, normalized, normalized_parts[-1]
        ).ratio() >= 0.82:
            continue
        normalized_parts.append(normalized)
    return " > ".join(normalized_parts)


def _build_procedural_page_catalog(
    metadata: list[dict],
) -> dict[tuple[str, str, int], tuple[int, ...]]:
    steps_by_section_page: dict[tuple[str, str], dict[int, set[int]]] = {}
    for item in metadata:
        source = str(item.get("source") or "").strip()
        section = _procedure_section_key(
            item.get("section_path") or item.get("heading") or ""
        )
        content = str(
            item.get("parent_text") or item.get("display_text") or item.get("text") or ""
        )
        step_numbers = {
            int(number)
            for number in re.findall(r"\b(?:buoc|step)\s*(\d+)\b", _fold(content))
        }
        if not source or not section or not step_numbers:
            continue
        try:
            page = int(item.get("page"))
        except (TypeError, ValueError):
            continue
        page_steps = steps_by_section_page.setdefault((source, section), {})
        page_steps.setdefault(page, set()).update(step_numbers)

    catalog: dict[tuple[str, str, int], tuple[int, ...]] = {}
    for (source, section), steps_by_page in steps_by_section_page.items():
        groups: list[list[int]] = []
        current_group: list[int] = []
        previous_page: int | None = None
        previous_max_step: int | None = None

        for page in sorted(steps_by_page):
            page_steps = steps_by_page[page]
            starts_new_sequence = (
                previous_page is not None
                and (
                    page - previous_page > 2
                    or (
                        previous_max_step is not None
                        and min(page_steps) <= previous_max_step
                    )
                )
            )
            if starts_new_sequence and current_group:
                groups.append(current_group)
                current_group = []

            current_group.append(page)
            previous_page = page
            previous_max_step = max(page_steps)

        if current_group:
            groups.append(current_group)

        for group in groups:
            ordered_group = tuple(group)
            for page in group:
                catalog[(source, section, page)] = ordered_group

    return catalog


def activate_resources(vector_store: VectorStore, bm25_retriever: BM25Retriever):
    global _resources, _temporal_catalog, _procedural_page_catalog
    _resources = (vector_store, bm25_retriever)
    _temporal_catalog = build_temporal_catalog(vector_store.metadata)
    _procedural_page_catalog = _build_procedural_page_catalog(vector_store.metadata)


def load_resources():
    vector_store = VectorStore(dim=768)
    bm25_retriever = BM25Retriever()

    if os.path.exists(os.path.join(VECTOR_STORE_DIR, "index.faiss")):
        vector_store.load(VECTOR_STORE_DIR)
    try:
        bm25_retriever.load(VECTOR_STORE_DIR)
    except Exception:
        pass

    activate_resources(vector_store, bm25_retriever)


def _normalize_query(query: str) -> str:
    query = unicodedata.normalize("NFC", query or "").replace("\u00a0", " ")
    query = re.sub(r"[\x00-\x1f\x7f]+", " ", query)
    return re.sub(r"\s+", " ", query).strip()


def _strip_accents(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text)
    return (
        "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
        .replace("đ", "d")
        .replace("Đ", "D")
    )


def _fold(text: str) -> str:
    return re.sub(r"\s+", " ", _strip_accents(text).casefold()).strip()


load_resources()


def _detect_exam_intent(query: str) -> str | None:
    normalized = _fold(query)
    if (
        "pea" in normalized
        or re.search(r"\bthi\s+thuc\s+hanh\b", normalized)
        or "phan mem thi thuc hanh" in normalized
    ):
        return "pea"
    if "eos" in normalized or "ly thuyet" in normalized:
        return "eos"
    if "e360" in normalized or "speaking" in normalized:
        return "e360"
    return None


def _intent_factor(source: str, text: str, intent: str | None) -> float:
    if not intent:
        return 1.0

    haystack = _fold(f"{source} {text}")
    present = {
        "pea": "pea" in haystack or "thuc hanh" in haystack,
        "eos": "eos" in haystack or "ly thuyet" in haystack,
        "e360": "e360" in haystack or "speaking" in haystack,
    }
    if present[intent]:
        return 1.12
    if any(present.values()):
        return 0.88
    return 1.0


def _query_identifiers(query: str) -> set[str]:
    identifiers = {
        match.casefold()
        for match in re.findall(
            r"(?<!\w)(?:[A-Za-z]{1,12}[-_.]?[A-Za-z0-9]*\d+[A-Za-z0-9_.-]*|\d{3,})(?!\w)",
            query,
        )
    }
    folded = query.casefold()
    identifiers.update(term for term in _DOMAIN_TERMS if term in folded)
    return identifiers


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"\w+", _fold(text), flags=re.UNICODE)
        if len(token) > 1 and token not in _STOPWORDS
    }


def _apply_rule_boost(result: dict, query: str, intent: str | None) -> dict:
    boosted = result.copy()
    searchable = " ".join(
        str(boosted.get(field, ""))
        for field in ("source", "heading", "section_path", "retrieval_text", "text")
    )
    searchable_folded = _fold(searchable)
    factor = _intent_factor(boosted.get("source", ""), searchable, intent)
    reasons = []

    identifiers = _query_identifiers(query)
    matched = {identifier for identifier in identifiers if _fold(identifier) in searchable_folded}
    if identifiers and matched == identifiers:
        factor *= 1.25
        reasons.append("all_identifiers")
    elif matched:
        factor *= 1.10
        reasons.append("some_identifiers")

    folded_query = _fold(query)
    if 3 <= len(folded_query.split()) <= 24 and folded_query in searchable_folded:
        factor *= 1.15
        reasons.append("exact_phrase")

    query_tokens = _tokens(query)
    heading_tokens = _tokens(
        f"{boosted.get('heading', '')} {boosted.get('section_path', '')}"
    )
    if query_tokens and len(query_tokens & heading_tokens) / len(query_tokens) >= 0.5:
        factor *= 1.08
        reasons.append("heading_match")

    boosted["rule_factor"] = min(max(factor, 0.80), 1.45)
    boosted["boost_reasons"] = reasons
    boosted["combined_score"] = (
        boosted.get("combined_score", 0.0) * boosted["rule_factor"]
    )
    return boosted


def _combine_hybrid_results(
    dense_results: list,
    sparse_results: list,
    metadata: list,
    dense_weight: float = DENSE_WEIGHT,
    bm25_weight: float = BM25_WEIGHT,
    rrf_k: int = RRF_K,
) -> list:
    """Fuse dense and BM25 rankings with weighted Reciprocal Rank Fusion."""
    scores: dict[int, float] = {}
    results: dict[int, dict] = {}

    for rank, result in enumerate(dense_results, start=1):
        index = result.get("index")
        if index is None:
            continue
        scores[index] = scores.get(index, 0.0) + dense_weight / (rrf_k + rank)
        item = result.copy()
        item["dense_rank"] = rank
        results[index] = item

    for rank, (index, bm25_score) in enumerate(sparse_results, start=1):
        scores[index] = scores.get(index, 0.0) + bm25_weight / (rrf_k + rank)
        if index in results:
            item = results[index]
        elif index < len(metadata):
            item = metadata[index].copy()
            item["index"] = index
            results[index] = item
        else:
            continue
        item["bm25_rank"] = rank
        item["bm25_score"] = bm25_score

    combined = []
    for index, score in scores.items():
        if index not in results:
            continue
        item = results[index].copy()
        item["combined_score"] = score
        item["matched_both"] = "dense_rank" in item and "bm25_rank" in item
        combined.append(item)

    return sorted(
        combined,
        key=lambda item: item.get("combined_score", 0.0),
        reverse=True,
    )


def _aggregate_parents(children: list) -> list:
    parents: dict[str, dict] = {}

    for rank, child in enumerate(children, start=1):
        parent_id = child.get("parent_id") or (
            f"{child.get('source')}::page-{child.get('page')}::index-{child.get('index')}"
        )
        if parent_id not in parents:
            content = (
                child.get("parent_text")
                or child.get("display_text")
                or child.get("text", "")
            ).strip()
            parents[parent_id] = {
                "parent_id": parent_id,
                "source": child.get("source", "unknown.pdf"),
                "page": child.get("page", 0),
                "heading": child.get("heading", ""),
                "section_path": child.get("section_path", ""),
                "content": content,
                "best_child_score": child.get("combined_score", 0.0),
                "best_child_rank": rank,
                "matched_children": [],
            }
            for field in (
                "family_id", "document_date", "date_source", "version_rank",
                "subtype", "temporal_status",
            ):
                if child.get(field) is not None:
                    parents[parent_id][field] = child.get(field)

        parent = parents[parent_id]
        parent["matched_children"].append(child)
        parent["best_child_score"] = max(
            parent["best_child_score"], child.get("combined_score", 0.0)
        )
        parent["best_child_rank"] = min(parent["best_child_rank"], rank)

    for parent in parents.values():
        extra_children = min(max(len(parent["matched_children"]) - 1, 0), 3)
        coverage_factor = 1.0 + 0.10 * math.log1p(extra_children)
        parent["combined_score"] = parent["best_child_score"] * coverage_factor

    return sorted(
        parents.values(),
        key=lambda item: (
            item.get("combined_score", 0.0),
            -item.get("best_child_rank", 9999),
        ),
        reverse=True,
    )


def _normalized_content(text: str) -> str:
    return re.sub(r"\W+", " ", _fold(text), flags=re.UNICODE).strip()


def _is_near_duplicate(content: str, selected_contents: list[str]) -> bool:
    normalized = _normalized_content(content)
    if not normalized:
        return True

    tokens = set(normalized.split())
    for previous in selected_contents:
        if normalized == previous:
            return True
        previous_tokens = set(previous.split())
        union = tokens | previous_tokens
        jaccard = len(tokens & previous_tokens) / len(union) if union else 1.0
        if jaccard >= 0.78:
            return True
        if SequenceMatcher(None, normalized, previous).ratio() >= 0.88:
            return True
    return False


def _select_context_parents(
    parents: list,
    top_k: int = FINAL_CONTEXT_TOP_K,
    max_characters: int = MAX_CONTEXT_CHARACTERS,
) -> list:
    selected = []
    selected_contents = []
    total_characters = 0

    for parent in parents:
        content = parent.get("content", "").strip()
        if _is_near_duplicate(content, selected_contents):
            continue
        if selected and total_characters + len(content) > max_characters:
            continue

        selected.append(parent)
        selected_contents.append(_normalized_content(content))
        total_characters += len(content)
        if len(selected) >= top_k:
            break

    return selected


def _has_sufficient_retrieval_signal(
    dense_results: list,
    sparse_results: list,
    min_dense_score: float = MIN_DENSE_SCORE,
    min_bm25_score: float = MIN_BM25_SCORE,
) -> bool:
    """Require at least one strong semantic or lexical retrieval signal."""
    top_dense_score = (
        dense_results[0].get("dense_score", 0.0) if dense_results else 0.0
    )
    top_bm25_score = sparse_results[0][1] if sparse_results else 0.0
    return (
        top_dense_score >= min_dense_score
        or top_bm25_score >= min_bm25_score
    )


def retrieve_context(query: str, top_k: int = FINAL_CONTEXT_TOP_K):
    vector_store, bm25_retriever = _resources

    if not vector_store.metadata and not bm25_retriever.corpus:
        return "", []

    search_query = _normalize_query(query)
    if not search_query:
        return "", []
    intent = _detect_exam_intent(search_query)

    dense_results = vector_store.search(search_query, top_k=DENSE_TOP_K)
    sparse_results = bm25_retriever.search(search_query, top_k=BM25_TOP_K)
    # Both retrievers can return weak neighbours for out-of-domain questions.
    if not _has_sufficient_retrieval_signal(dense_results, sparse_results):
        return "", []

    combined = _combine_hybrid_results(
        dense_results, sparse_results, vector_store.metadata
    )
    if not combined:
        return "", []

    boosted = [_apply_rule_boost(result, search_query, intent) for result in combined]
    boosted.sort(key=lambda item: item.get("combined_score", 0.0), reverse=True)

    child_candidates = boosted[:FUSION_TOP_K]
    parent_candidates = _aggregate_parents(child_candidates)
    parent_candidates = resolve_temporal_evidence(
        parent_candidates,
        search_query,
        _temporal_catalog,
        enabled=TEMPORAL_RESOLVER_ENABLED,
    )
    final_parents = _select_context_parents(parent_candidates, top_k=top_k)

    context_parts = []
    source_documents = []
    explicit_latest_context = any(
        item.get("temporal_action") == "current_explicit_latest_query"
        for item in final_parents
    )
    for position, item in enumerate(final_parents, start=1):
        evidence_id = f"E{position}"
        if explicit_latest_context:
            source_label = "Supporting PDF (filename is not product version metadata)"
            section = item.get("heading") or "Không có"
        else:
            source_label = item["source"]
            section = item.get("section_path") or item.get("heading") or "Không có"
        release_metadata = ""
        if item.get("subtype") == "release_notice" and item.get("document_date"):
            release_metadata = (
                f"Product release date: {item['document_date']}\n"
                "Date semantics: this is the product/package version date; "
                "a date in Source may only be the document publication date.\n"
            )
        context_parts.append(
            f"[{evidence_id}]\n"
            f"Source: {source_label}\n"
            f"Page: {item['page']}\n"
            f"Section: {section}\n"
            f"{release_metadata}"
            f"Content:\n{item['content']}"
        )
        source_documents.append(
            {
                "evidence_id": evidence_id,
                "file_name": item["source"],
                "source": item["source"],
                "page": item["page"],
                "parent_id": item["parent_id"],
                "score": item.get("combined_score", 0.0),
                "matched_child_count": len(item.get("matched_children", [])),
                "family_id": item.get("family_id"),
                "document_date": item.get("document_date"),
                "version_rank": item.get("version_rank"),
                "subtype": item.get("subtype"),
                "temporal_action": item.get("temporal_action"),
                "historical": item.get("historical", False),
                "procedural_pages": list(
                    _procedural_page_catalog.get(
                        (
                            item["source"],
                            _procedure_section_key(
                                item.get("section_path") or item.get("heading") or ""
                            ),
                            int(item["page"]),
                        ),
                        (),
                    )
                ),
            }
        )

    return "\n\n".join(context_parts), source_documents
