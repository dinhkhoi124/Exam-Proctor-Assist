"""Conditional family-aware temporal evidence resolution for P0-T.

Only reviewable, verified multi-version families are eligible. If those
prerequisites are absent, the resolver returns the original P0 list unchanged.
"""

from __future__ import annotations

import json
import math
import os
import re
import unicodedata
from collections import defaultdict

from rank_bm25 import BM25Okapi


DEFAULT_MANIFEST_PATH = os.path.join(os.path.dirname(__file__), "temporal_manifest.json")
DEFAULT_SCORE_RATIO = 0.95
DEFAULT_MINIMUM_COVERAGE = 0.18

_CLAIM_STOPWORDS = {
    "ai", "bao", "bi", "cach", "can", "co", "con", "cua", "cho", "duoc",
    "gi", "hay", "hien", "huong", "khi", "la", "lam", "mot", "nao", "nhu",
    "nhung", "phai", "sau", "su", "tai", "theo", "thi", "trong", "truoc",
    "va", "ve", "voi",
}
_DOMAIN_TERMS = {
    "eos", "eosclient", "pea", "pealogin", "e360", "usb", "fu-exam", "wifi",
    "wi-fi",
}


def load_temporal_manifest(path: str = DEFAULT_MANIFEST_PATH) -> dict[str, dict]:
    """Load and validate the source-keyed, human-reviewable temporal manifest."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        return {}

    documents = payload.get("documents", [])
    manifest: dict[str, dict] = {}
    for item in documents:
        source = str(item.get("source", "")).strip()
        family_id = str(item.get("family_id", "")).strip()
        try:
            version_rank = int(item.get("version_rank"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid temporal version_rank for {source!r}") from exc
        if not source or not family_id or version_rank < 1:
            raise ValueError("Temporal manifest entries require source, family_id and version_rank")
        if source in manifest:
            raise ValueError(f"Duplicate temporal manifest source: {source}")
        manifest[source] = {
            "family_id": family_id,
            "document_date": item.get("document_date"),
            "date_source": item.get("date_source", "unknown"),
            "version_rank": version_rank,
            "subtype": item.get("subtype", "general"),
            "temporal_status": item.get("temporal_status", "provisional"),
        }

    for item in payload.get("page_overrides", []):
        source = str(item.get("source", "")).strip()
        family_id = str(item.get("family_id", "")).strip()
        try:
            page = int(item.get("page"))
            version_rank = int(item.get("version_rank"))
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid temporal page override for {source!r}") from exc
        if not source or not family_id or page < 1 or version_rank < 1:
            raise ValueError(
                "Temporal page overrides require source, page, family_id and version_rank"
            )
        source_metadata = manifest.setdefault(source, {})
        page_overrides = source_metadata.setdefault("_page_overrides", {})
        page_key = str(page)
        if page_key in page_overrides:
            raise ValueError(f"Duplicate temporal page override: {source}, page {page}")
        page_overrides[page_key] = {
            "family_id": family_id,
            "document_date": item.get("document_date"),
            "date_source": item.get("date_source", "unknown"),
            "version_rank": version_rank,
            "subtype": item.get("subtype", "general"),
            "temporal_status": item.get("temporal_status", "provisional"),
            "verified_visual_fact": item.get("verified_visual_fact"),
        }
    return manifest


def build_temporal_catalog(metadata: list[dict]) -> dict[str, dict]:
    """Return only verified families containing at least two indexed versions."""
    families: dict[str, dict[int, set[str]]] = defaultdict(lambda: defaultdict(set))
    candidates: dict[str, dict[int, dict[str, dict]]] = defaultdict(
        lambda: defaultdict(dict)
    )
    invalid_families: set[str] = set()
    for item in metadata:
        family_id = item.get("family_id")
        if not family_id:
            continue
        if item.get("temporal_status") != "verified":
            invalid_families.add(str(family_id))
            continue
        try:
            version_rank = int(item.get("version_rank"))
        except (TypeError, ValueError):
            invalid_families.add(str(family_id))
            continue
        family_key = str(family_id)
        source = str(item.get("source", ""))
        families[family_key][version_rank].add(source)
        parent_id = str(
            item.get("parent_id")
            or f"{source}::page-{item.get('page', 0)}::temporal-catalog"
        )
        if parent_id not in candidates[family_key][version_rank]:
            candidates[family_key][version_rank][parent_id] = {
                "parent_id": parent_id,
                "source": source,
                "page": item.get("page", 0),
                "heading": item.get("heading", ""),
                "section_path": item.get("section_path", ""),
                "content": (
                    item.get("content")
                    or item.get("parent_text")
                    or item.get("display_text")
                    or item.get("text", "")
                ),
                "combined_score": float(item.get("combined_score", 0.0)),
                "family_id": family_key,
                "document_date": item.get("document_date"),
                "date_source": item.get("date_source"),
                "version_rank": version_rank,
                "subtype": item.get("subtype"),
                "temporal_status": item.get("temporal_status"),
                "matched_children": [item],
            }

    catalog = {}
    for family_id, versions in families.items():
        if family_id in invalid_families or len(versions) < 2:
            continue
        catalog[family_id] = {
            "newest_version_rank": max(versions),
            "version_ranks": tuple(sorted(versions)),
            "newest_candidates": tuple(
                candidates[family_id][max(versions)].values()
            ),
        }
    return catalog


def _fold(text: str) -> str:
    normalized = unicodedata.normalize("NFD", str(text or "")).casefold().replace("đ", "d")
    return "".join(char for char in normalized if unicodedata.category(char) != "Mn")


def _ordered_claim_tokens(text: str) -> list[str]:
    return [
        token
        for token in re.findall(r"[a-z0-9]+(?:[-_.][a-z0-9]+)*", _fold(text))
        if len(token) > 1 and token not in _CLAIM_STOPWORDS
    ]


def _query_identifiers(query: str) -> set[str]:
    identifiers = {
        match.casefold()
        for match in re.findall(
            r"(?<!\w)(?:[A-Za-z]{1,12}[-_.]?[A-Za-z0-9]*\d+[A-Za-z0-9_.-]*|\d{3,})(?!\w)",
            query,
        )
    }
    folded = _fold(query)
    identifiers.update(term for term in _DOMAIN_TERMS if term in folded)
    return {_fold(identifier) for identifier in identifiers}


def _asks_for_latest_version(query: str) -> bool:
    folded = _fold(query)
    latest_markers = (
        "moi nhat",
        "phien ban moi",
        "ban cap nhat moi",
        "hien tai",
        "latest version",
        "current version",
        "current release",
    )
    return any(marker in folded for marker in latest_markers)


def _enrich_claim_features(group: list[dict], query: str) -> list[dict]:
    query_tokens = _ordered_claim_tokens(query)
    unique_query = set(query_tokens)
    query_bigrams = set(zip(query_tokens, query_tokens[1:]))
    document_tokens = [
        _ordered_claim_tokens(
            " ".join(
                [
                    str(item.get("heading", "")),
                    str(item.get("section_path", "")),
                    str(item.get("content", "")),
                ]
            )
        )
        for item in group
    ]
    document_sets = [set(tokens) for tokens in document_tokens]
    document_count = max(len(document_sets), 1)
    document_frequency = {
        term: sum(term in tokens for tokens in document_sets) for term in unique_query
    }
    weights = {
        term: 1.0 + math.log((document_count + 1) / (document_frequency[term] + 1))
        for term in unique_query
    }
    denominator = sum(weights.values()) or 1.0
    raw_bm25 = (
        list(BM25Okapi(document_tokens).get_scores(query_tokens))
        if query_tokens and any(document_tokens)
        else [0.0] * len(group)
    )
    bm25_max = max(raw_bm25, default=0.0)
    identifiers = _query_identifiers(query)

    output = []
    for item, tokens, token_set, bm25_value in zip(
        group, document_tokens, document_sets, raw_bm25
    ):
        weighted_coverage = (
            sum(weights[token] for token in unique_query if token in token_set) / denominator
        )
        content_bigrams = set(zip(tokens, tokens[1:]))
        bigram_coverage = (
            len(query_bigrams & content_bigrams) / len(query_bigrams)
            if query_bigrams
            else 0.0
        )
        content_folded = _fold(f"{item.get('source', '')} {item.get('content', '')}")
        identifier_coverage = (
            sum(identifier in content_folded for identifier in identifiers) / len(identifiers)
            if identifiers
            else 0.0
        )
        bm25_norm = float(bm25_value) / bm25_max if bm25_max > 0 else 0.0
        relevance = float(item.get("relevance_norm", 0.0))
        differential_score = (
            0.40 * weighted_coverage
            + 0.20 * bigram_coverage
            + 0.20 * bm25_norm
            + 0.10 * identifier_coverage
            + 0.10 * relevance
        )
        enriched = item.copy()
        enriched.update(
            {
                "weighted_claim_coverage": weighted_coverage,
                "claim_bigram_coverage": bigram_coverage,
                "claim_bm25_norm": bm25_norm,
                "identifier_coverage": identifier_coverage,
                "differential_claim_score": differential_score,
            }
        )
        output.append(enriched)
    return output


def _inject_missing_latest_candidates(
    parents: list[dict], query: str, catalog: dict[str, dict]
) -> list[dict]:
    """Add the best indexed current page when a latest query retrieved only history."""
    if not _asks_for_latest_version(query):
        return parents

    existing_parent_ids = {str(item.get("parent_id", "")) for item in parents}
    global_top_score = max(
        (float(item.get("combined_score", 0.0)) for item in parents),
        default=0.0,
    )
    family_scores: dict[str, float] = defaultdict(float)
    for item in parents:
        family_id = str(item.get("family_id", ""))
        if family_id in catalog and item.get("temporal_status") == "verified":
            family_scores[family_id] = max(
                family_scores[family_id], float(item.get("combined_score", 0.0))
            )

    expanded = list(parents)
    for family_id, inherited_score in family_scores.items():
        newest_rank = int(catalog[family_id]["newest_version_rank"])
        if any(
            str(item.get("family_id", "")) == family_id
            and int(item.get("version_rank", 0)) == newest_rank
            for item in parents
        ):
            continue

        candidates = [
            dict(candidate, relevance_norm=0.0)
            for candidate in catalog[family_id].get("newest_candidates", ())
            if str(candidate.get("parent_id", "")) not in existing_parent_ids
        ]
        if not candidates:
            continue
        enriched = _enrich_claim_features(candidates, query)
        best = max(
            enriched,
            key=lambda item: (
                item["differential_claim_score"],
                item["weighted_claim_coverage"],
            ),
        )
        # Put an explicitly requested current release ahead of a document-level
        # publication date. Temporal version selection, not synthetic dense
        # similarity, is the reason this indexed page is being added.
        best["combined_score"] = max(inherited_score, global_top_score * 1.05)
        best["temporal_injected"] = True
        expanded.append(best)
        existing_parent_ids.add(str(best.get("parent_id", "")))
    return expanded


def resolve_temporal_evidence(
    parents: list[dict],
    query: str,
    catalog: dict[str, dict],
    *,
    enabled: bool = True,
    score_ratio: float = DEFAULT_SCORE_RATIO,
    minimum_coverage: float = DEFAULT_MINIMUM_COVERAGE,
) -> list[dict]:
    """Select current or controlled historical evidence inside eligible families.

    Selection uses the benchmarked differential-claim policy within a family,
    then restores P0 ``combined_score`` ordering across unrelated families.
    """
    if not enabled or not parents or not catalog:
        return parents

    parents = _inject_missing_latest_candidates(parents, query, catalog)

    eligible_groups: dict[str, list[dict]] = defaultdict(list)
    passthrough = []
    for item in parents:
        family_id = str(item.get("family_id", ""))
        if family_id in catalog and item.get("temporal_status") == "verified":
            eligible_groups[family_id].append(item)
        else:
            passthrough.append(item)
    if not eligible_groups:
        return parents

    top_score = max(float(item.get("combined_score", 0.0)) for item in parents) or 1.0
    resolved = list(passthrough)
    for family_id, raw_group in eligible_groups.items():
        normalized_group = []
        for item in raw_group:
            enriched = item.copy()
            enriched["relevance_norm"] = float(item.get("combined_score", 0.0)) / top_score
            normalized_group.append(enriched)
        group = _enrich_claim_features(normalized_group, query)
        newest = int(catalog[family_id]["newest_version_rank"])
        latest = [item for item in group if int(item["version_rank"]) == newest]
        older = [item for item in group if int(item["version_rank"]) < newest]

        if not older:
            resolved.extend(
                {**item, "temporal_action": "only_or_current_version_v3", "historical": False}
                for item in latest
            )
            continue
        if not latest:
            resolved.extend(
                {
                    **item,
                    "temporal_action": "historical_fallback_latest_not_retrieved_v3",
                    "historical": True,
                }
                for item in older
            )
            continue

        if _asks_for_latest_version(query):
            resolved.extend(
                {
                    **item,
                    "temporal_action": "current_explicit_latest_query",
                    "historical": False,
                }
                for item in latest
            )
            continue

        best_latest = max(
            latest,
            key=lambda item: (item["differential_claim_score"], item["relevance_norm"]),
        )
        best_old = max(
            older,
            key=lambda item: (item["differential_claim_score"], item["relevance_norm"]),
        )
        latest_has_claim = (
            best_latest["weighted_claim_coverage"] >= minimum_coverage
            and best_latest["differential_claim_score"]
            >= score_ratio * max(best_old["differential_claim_score"], 1e-9)
        )
        old_specific_advantage = (
            best_old["weighted_claim_coverage"] - best_latest["weighted_claim_coverage"] >= 0.12
            and best_old["claim_bm25_norm"] - best_latest["claim_bm25_norm"] >= 0.15
        )
        latest_identifier_advantage = (
            best_latest["identifier_coverage"] > best_old["identifier_coverage"]
            and best_latest["weighted_claim_coverage"] >= minimum_coverage
        )
        if latest_identifier_advantage:
            latest_has_claim = True
        elif old_specific_advantage:
            latest_has_claim = False

        if latest_has_claim:
            resolved.extend(
                {
                    **item,
                    "temporal_action": "current_differential_claim_match",
                    "historical": False,
                }
                for item in latest
            )
        else:
            resolved.extend(
                {
                    **item,
                    "temporal_action": "controlled_differential_fallback",
                    "historical": True,
                }
                for item in older
            )

    return sorted(
        resolved,
        key=lambda item: float(item.get("combined_score", 0.0)),
        reverse=True,
    )
