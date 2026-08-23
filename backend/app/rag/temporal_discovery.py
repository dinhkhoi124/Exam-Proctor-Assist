"""Deterministic temporal metadata discovery for RAG documents.

This module deliberately does not call an LLM. It extracts version dates from
file names and page text, discovers document families from generic title/content
similarity, and assigns ranks by normalized date. Human-verified manifest values
are merged later and always take precedence.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from collections import defaultdict
from datetime import date
from difflib import SequenceMatcher
from pathlib import Path


DEFAULT_GENERATED_MANIFEST_PATH = os.path.join(
    os.path.dirname(__file__), "temporal_manifest.generated.json"
)

_DATE_PATTERN = re.compile(
    r"(?<!\d)(?P<day>0?[1-9]|[12]\d|3[01])[./_-]"
    r"(?P<month>0?[1-9]|1[0-2])[./_-]"
    r"(?P<year>20\d{2}|\d{2})(?!\d)"
)

_RELEASE_POSITIVE_MARKERS = (
    "phien ban", "version", "release", "released", "cap nhat", "update",
    "download", "tai phan mem", "goi cai dat", "installer", ".zip", ".exe",
    ".msi", ".apk", ".dmg", "client",
)
_RELEASE_NEGATIVE_MARKERS = ("ngay thi", "lich thi", "han nop", "ngay ban hanh")
_RELEASE_PRODUCT_NOISE = {
    "ban", "build", "cap", "client", "download", "file", "goi", "installer",
    "latest", "laptop", "mac", "mobile", "moi", "ngay", "oncampus", "package",
    "phan", "release", "released", "software", "tai", "update", "updated",
    "version", "win", "windows", "x64", "x86", "zip",
}


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFD", str(value or "")).casefold()
    normalized = normalized.replace("đ", "d")
    return "".join(
        character for character in normalized
        if unicodedata.category(character) != "Mn"
    )


def extract_dates(value: str) -> list[tuple[date, str, int]]:
    """Return valid dates, their raw spelling, and start position."""
    output = []
    for match in _DATE_PATTERN.finditer(str(value or "")):
        year = int(match.group("year"))
        if year < 100:
            year += 2000
        try:
            parsed = date(year, int(match.group("month")), int(match.group("day")))
        except ValueError:
            continue
        output.append((parsed, match.group(0), match.start()))
    return output


_TITLE_NOISE_TOKENS = {
    "ban", "copy", "final", "latest", "moi", "new", "update", "updated",
    "ver", "version",
}
_TITLE_CONNECTOR_TOKENS = {"cho", "danh", "ky", "tu"}
_AUDIENCE_TOKENS = {
    "giang", "giam", "gv", "sinh", "speaking", "sv", "vien",
}
_ABBREVIATIONS = {
    "hd": ("huong", "dan"),
    "hdsd": ("huong", "dan", "su", "dung"),
    "ht": ("he", "thong"),
    "sd": ("su", "dung"),
}
_CONTENT_STOPWORDS = {
    "bi", "cac", "cho", "co", "cua", "da", "de", "duoc", "gi", "khi",
    "khong", "la", "lai", "mot", "nay", "neu", "nhap", "nhan", "nhung",
    "sau", "se", "tai", "theo", "thi", "thong", "tren", "tu", "va", "vao",
    "voi",
}


def _title_profile(source: str) -> dict:
    """Build a domain-agnostic title fingerprint after removing version noise."""
    folded = _fold(Path(source).stem)
    folded = _DATE_PATTERN.sub(" ", folded)
    folded = re.sub(r"^\s*\d+\s*[.)_-]+\s*", " ", folded)
    folded = re.sub(
        r"\b(?:fall|spring|summer|winter|autumn|su|sp|fa)\s*(?:20)?\d{2}\b",
        " ",
        folded,
    )
    raw_tokens = re.findall(r"[a-z][a-z0-9]*", folded)
    expanded = []
    for token in raw_tokens:
        if token in _TITLE_NOISE_TOKENS or token.isdigit():
            continue
        expanded.extend(_ABBREVIATIONS.get(token, (token,)))

    title_text = " ".join(expanded)
    if "speaking" in expanded:
        subtype = "speaking"
    elif re.search(r"\b(?:gv|giam thi|giang vien|coi thi)\b", title_text):
        subtype = "invigilator"
    elif re.search(r"\b(?:sv|sinh vien)\b", title_text):
        subtype = "student"
    else:
        subtype = "general"

    # Audience is represented separately so a trailing "- GV" does not create
    # a new topic, while incompatible declared audiences still remain separate.
    canonical_tokens = [
        token for token in expanded
        if token not in _AUDIENCE_TOKENS and token not in _TITLE_CONNECTOR_TOKENS
    ]
    canonical = " ".join(dict.fromkeys(canonical_tokens)).strip() or "document"
    return {
        "canonical": canonical,
        "tokens": set(canonical_tokens),
        "subtype": subtype,
    }


def _infer_content_subtype(title_subtype: str, content: str) -> str:
    """Infer a generic audience only when the title does not declare one."""
    if title_subtype != "general":
        return title_subtype
    sample = _fold(content[:12000])
    speaking = len(re.findall(r"\bspeaking\b", sample))
    invigilator = len(re.findall(r"\b(?:giam thi|giang vien|coi thi)\b", sample))
    student = len(re.findall(r"\b(?:sinh vien|hoc vien)\b", sample))
    if speaking >= 2:
        return "speaking"
    if invigilator >= 2 and invigilator >= max(2, student * 0.35):
        return "invigilator"
    if student >= 3 and invigilator == 0:
        return "student"
    return "general"


def _content_terms(content: str) -> set[str]:
    tokens = [
        token for token in re.findall(r"[a-z][a-z0-9]{1,}", _fold(content[:20000]))
        if token not in _CONTENT_STOPWORDS and not token.isdigit()
    ]
    return set(tokens)


def _compatible_subtypes(left: str, right: str) -> bool:
    if left == right:
        return True
    if "speaking" in {left, right}:
        return False
    return "general" in {left, right}


def _profile_similarity(left: dict, right: dict) -> tuple[float, float, float]:
    left_tokens = left["tokens"]
    right_tokens = right["tokens"]
    union = left_tokens | right_tokens
    title_jaccard = len(left_tokens & right_tokens) / max(len(union), 1)
    title_sequence = SequenceMatcher(
        None, left["canonical"], right["canonical"]
    ).ratio()
    content_union = left["content_terms"] | right["content_terms"]
    content_jaccard = len(
        left["content_terms"] & right["content_terms"]
    ) / max(len(content_union), 1)
    return title_jaccard, title_sequence, content_jaccard


def _should_link_profiles(left: dict, right: dict) -> tuple[bool, float]:
    if not _compatible_subtypes(left["subtype"], right["subtype"]):
        return False, 0.0
    title_jaccard, title_sequence, content_jaccard = _profile_similarity(left, right)
    exact_title = left["canonical"] == right["canonical"]
    if exact_title and left["canonical"] != "document":
        score = 0.97 if left["subtype"] == right["subtype"] else 0.90
        return True, score
    score = 0.50 * title_jaccard + 0.20 * title_sequence + 0.30 * content_jaccard
    strong_title = title_jaccard >= 0.72 and title_sequence >= 0.78
    corroborated = title_jaccard >= 0.55 and content_jaccard >= 0.55
    return strong_title or corroborated, min(score, 0.94)


def _family_id(canonical: str, subtype: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", canonical).strip("_")[:42] or "document"
    identity = f"{canonical}|{subtype}".encode("utf-8")
    digest = hashlib.sha1(identity).hexdigest()[:8]
    return f"auto_{slug}_{subtype}_{digest}"


def _normalize_product_key(value: str) -> str:
    tokens = [
        token
        for token in re.findall(r"[a-z][a-z0-9]{1,}", _fold(value))
        if token not in _RELEASE_PRODUCT_NOISE and not token.isdigit()
    ]
    if not tokens:
        return ""
    product = tokens[0]
    # Package names commonly append a deployment role to the stable product
    # name (for example ProductClient or ProductInstaller). Fuzzy suffix
    # matching tolerates a one-character OCR error in that generic role while
    # leaving the actual product stem data-driven.
    for suffix in ("installer", "launcher", "desktop", "client", "agent", "app"):
        matches = []
        for tail_length in (len(suffix), len(suffix) - 1, len(suffix) + 1):
            if tail_length < 3 or len(product) - tail_length < 3:
                continue
            tail = product[-tail_length:]
            similarity = SequenceMatcher(None, tail, suffix).ratio()
            if similarity >= 0.80:
                matches.append((similarity, -abs(tail_length - len(suffix)), tail_length))
        if matches:
            _, _, best_tail_length = max(matches)
            return product[:-best_tail_length]
    return product


def _release_family_id(product_key: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", product_key).strip("_")[:42] or "product"
    digest = hashlib.sha1(product_key.encode("utf-8")).hexdigest()[:8]
    return f"auto_release_{slug}_{digest}"


def _product_near_date(page_text: str, position: int, raw_date: str) -> str:
    start = max(position - 140, 0)
    end = min(position + len(raw_date) + 80, len(page_text))
    context = _fold(page_text[start:end])
    date_offset = position - start
    before_date = context[:date_offset]

    # Prefer an artifact-style identifier. This remains product-agnostic while
    # handling names such as FooClient_29.07.2026.zip.
    artifact_candidates = re.findall(
        r"\b([a-z][a-z0-9]{2,}(?:client|installer|launcher|desktop|agent|app))\b",
        before_date,
    )
    if artifact_candidates:
        return _normalize_product_key(artifact_candidates[-1])

    # Otherwise use the value following a generic release/software phrase.
    labelled_candidates = re.findall(
        r"\b(?:phien ban|version|phan mem|software|ung dung|application|package)\s+"
        r"([a-z][a-z0-9]{1,})\b",
        before_date,
    )
    for candidate in reversed(labelled_candidates):
        product = _normalize_product_key(candidate)
        if product:
            return product

    # Final fallback: nearest distinctive token before the date. It is only
    # accepted when the surrounding text already contains release evidence.
    for candidate in reversed(re.findall(r"[a-z][a-z0-9]{2,}", before_date)):
        product = _normalize_product_key(candidate)
        if product:
            return product
    return ""


def _discover_document_families(pages_by_source: dict[str, list[dict]]) -> dict[str, dict]:
    """Cluster document versions using generic title/content fingerprints."""
    profiles = []
    for source, pages in sorted(pages_by_source.items(), key=lambda item: item[0].casefold()):
        title = _title_profile(source)
        content = "\n".join(str(page.get("content", "")) for page in pages)
        subtype = _infer_content_subtype(title["subtype"], content)
        profiles.append({
            "source": source,
            "canonical": title["canonical"],
            "tokens": title["tokens"],
            "subtype": subtype,
            "content_terms": _content_terms(content),
        })

    link_scores: dict[tuple[int, int], float] = {}
    for left in range(len(profiles)):
        for right in range(left + 1, len(profiles)):
            linked, score = _should_link_profiles(profiles[left], profiles[right])
            if linked:
                link_scores[(left, right)] = score

    # Complete-link clustering prevents a generic document from acting as a
    # bridge between two otherwise incompatible version families. Two clusters
    # merge only when every cross-cluster document pair passes the generic
    # similarity gate.
    components: list[list[int]] = [[index] for index in range(len(profiles))]
    while True:
        best: tuple[float, int, int] | None = None
        for left_cluster in range(len(components)):
            for right_cluster in range(left_cluster + 1, len(components)):
                cross_scores = []
                for left in components[left_cluster]:
                    for right in components[right_cluster]:
                        pair = (min(left, right), max(left, right))
                        if pair not in link_scores:
                            cross_scores = []
                            break
                        cross_scores.append(link_scores[pair])
                    if not cross_scores:
                        break
                if not cross_scores:
                    continue
                candidate = (min(cross_scores), left_cluster, right_cluster)
                if best is None or candidate[0] > best[0]:
                    best = candidate
        if best is None:
            break
        _, left_cluster, right_cluster = best
        components[left_cluster] = sorted(
            components[left_cluster] + components[right_cluster]
        )
        components.pop(right_cluster)

    output = {}
    for indices in components:
        counts: dict[str, int] = defaultdict(int)
        for index in indices:
            counts[profiles[index]["canonical"]] += 1
        canonical = min(counts, key=lambda item: (-counts[item], len(item), item))
        subtype_counts: dict[str, int] = defaultdict(int)
        for index in indices:
            subtype_counts[profiles[index]["subtype"]] += 1
        subtype = min(
            subtype_counts,
            key=lambda item: (-subtype_counts[item], item == "general", item),
        )
        family_id = _family_id(canonical, subtype)
        component_scores = [
            score for (left, right), score in link_scores.items()
            if left in indices and right in indices
        ]
        cluster_confidence = (
            sum(component_scores) / len(component_scores)
            if component_scores else 0.72
        )
        for index in indices:
            output[profiles[index]["source"]] = {
                "family_id": family_id,
                "family_fingerprint": canonical,
                "subtype": subtype,
                "cluster_size": len(indices),
                "cluster_confidence": round(cluster_confidence, 3),
            }
    return output


def _best_release_date(page_text: str) -> tuple[date, str, float, str] | None:
    folded = _fold(page_text)
    if not any(marker in folded for marker in _RELEASE_POSITIVE_MARKERS):
        return None

    candidates = []
    for parsed, raw, position in extract_dates(page_text):
        start = max(position - 100, 0)
        end = min(position + len(raw) + 100, len(page_text))
        context = _fold(page_text[start:end])
        product_key = _product_near_date(page_text, position, raw)
        if not product_key:
            continue
        score = 0.55
        score += 0.12 * min(
            sum(marker in context for marker in _RELEASE_POSITIVE_MARKERS), 2
        )
        score += 0.15
        score -= 0.15 * sum(marker in context for marker in _RELEASE_NEGATIVE_MARKERS)
        candidates.append((score, parsed, raw, product_key))
    if not candidates:
        return None
    score, parsed, raw, product_key = max(
        candidates, key=lambda item: (item[0], item[1])
    )
    return parsed, raw, min(max(score, 0.0), 0.99), product_key


def _assign_version_ranks(manifest: dict[str, dict]) -> None:
    families: dict[str, set[str]] = defaultdict(set)
    records = []
    for source, metadata in manifest.items():
        if metadata.get("family_id") and metadata.get("document_date"):
            records.append(metadata)
            families[str(metadata["family_id"])].add(str(metadata["document_date"]))
        for page_metadata in metadata.get("_page_overrides", {}).values():
            if page_metadata.get("family_id") and page_metadata.get("document_date"):
                records.append(page_metadata)
                families[str(page_metadata["family_id"])].add(
                    str(page_metadata["document_date"])
                )

    ranks = {
        family_id: {
            document_date: rank
            for rank, document_date in enumerate(sorted(document_dates), start=1)
        }
        for family_id, document_dates in families.items()
    }
    for metadata in records:
        metadata["version_rank"] = ranks[str(metadata["family_id"])][
            str(metadata["document_date"])
        ]


def discover_temporal_metadata(documents: list[dict]) -> dict[str, dict]:
    """Discover source- and page-level temporal metadata from parsed PDF text."""
    pages_by_source: dict[str, list[dict]] = defaultdict(list)
    for document in documents:
        source = str(document.get("source", "")).strip()
        if source:
            pages_by_source[source].append(document)

    discovered_families = _discover_document_families(pages_by_source)
    dated_members: dict[str, int] = defaultdict(int)
    for source, family in discovered_families.items():
        if extract_dates(Path(source).stem):
            dated_members[str(family["family_id"])] += 1

    manifest: dict[str, dict] = {}
    for source, pages in pages_by_source.items():
        source_metadata: dict = {}
        family = discovered_families[source]
        filename_dates = extract_dates(Path(source).stem)
        if filename_dates:
            document_date, raw_date, _ = max(filename_dates, key=lambda item: item[0])
            cluster_confidence = float(family["cluster_confidence"])
            is_verified_family = (
                dated_members[str(family["family_id"])] >= 2
                and cluster_confidence >= 0.85
            )
            source_metadata.update(
                {
                    "family_id": family["family_id"],
                    "family_fingerprint": family["family_fingerprint"],
                    "family_discovery": "auto_similarity_v1",
                    "document_date": document_date.isoformat(),
                    "date_source": "filename_auto",
                    "raw_date": raw_date,
                    "subtype": family["subtype"],
                    "cluster_size": family["cluster_size"],
                    "temporal_status": (
                        "verified" if is_verified_family else "provisional"
                    ),
                    "temporal_confidence": round(
                        min(0.95, cluster_confidence), 3
                    ),
                }
            )

        page_overrides = {}
        for page in pages:
            release = _best_release_date(str(page.get("content", "")))
            if not release:
                continue
            release_date, raw_date, confidence, product_key = release
            if confidence < 0.79:
                continue
            page_overrides[str(int(page.get("page", 0)))] = {
                "family_id": _release_family_id(product_key),
                "family_fingerprint": product_key,
                "family_discovery": "auto_release_context_v2",
                "document_date": release_date.isoformat(),
                "date_source": "content_auto",
                "raw_date": raw_date,
                "subtype": "release_notice",
                "temporal_status": "verified",
                "temporal_confidence": round(confidence, 3),
            }
        if page_overrides:
            source_metadata["_page_overrides"] = page_overrides
        if source_metadata:
            manifest[source] = source_metadata

    _assign_version_ranks(manifest)
    return manifest


def merge_temporal_metadata(
    generated: dict[str, dict], manual: dict[str, dict]
) -> dict[str, dict]:
    """Merge metadata while giving human-reviewed values absolute precedence."""
    merged = {
        source: {
            **metadata,
            **(
                {"_page_overrides": dict(metadata.get("_page_overrides", {}))}
                if metadata.get("_page_overrides")
                else {}
            ),
        }
        for source, metadata in generated.items()
    }
    for source, manual_metadata in manual.items():
        target = merged.setdefault(source, {})
        generated_pages = dict(target.get("_page_overrides", {}))
        manual_pages = dict(manual_metadata.get("_page_overrides", {}))
        target.update(
            {
                key: value
                for key, value in manual_metadata.items()
                if key != "_page_overrides"
            }
        )
        if generated_pages or manual_pages:
            generated_pages.update(manual_pages)
            target["_page_overrides"] = generated_pages
    # Rank is derived data. Recompute it across the effective manifest so newly
    # discovered historical versions cannot conflict with stale manual ranks.
    _assign_version_ranks(merged)
    return merged


def save_generated_manifest(
    manifest: dict[str, dict], path: str = DEFAULT_GENERATED_MANIFEST_PATH
) -> None:
    """Persist a human-readable diagnostic snapshot of automatic discovery."""
    documents = []
    page_overrides = []
    for source, metadata in sorted(manifest.items(), key=lambda item: item[0].casefold()):
        document_metadata = {
            key: value
            for key, value in metadata.items()
            if key != "_page_overrides"
        }
        if document_metadata:
            documents.append({"source": source, **document_metadata})
        for page, page_metadata in sorted(
            metadata.get("_page_overrides", {}).items(), key=lambda item: int(item[0])
        ):
            page_overrides.append(
                {"source": source, "page": int(page), **page_metadata}
            )
    payload = {
        "schema_version": 1,
        "generator": "deterministic_no_llm",
        "documents": documents,
        "page_overrides": page_overrides,
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
