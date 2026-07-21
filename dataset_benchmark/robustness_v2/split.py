"""Deterministic semantic grouping and leakage audits."""

from __future__ import annotations

from collections import defaultdict
import random
from typing import Iterable

from dataset_benchmark.scripts.metrics import normalize_text


def token_jaccard(first: str, second: str) -> float:
    first_tokens = set(normalize_text(first).split())
    second_tokens = set(normalize_text(second).split())
    union = first_tokens | second_tokens
    return len(first_tokens & second_tokens) / len(union) if union else 1.0


def semantic_clusters(rows: Iterable[dict], threshold: float) -> dict[int, str]:
    """Group normalized/near-duplicate transcripts using deterministic union-find."""

    if not 0 <= threshold <= 1:
        raise ValueError("semantic similarity threshold must be in [0, 1]")
    items = sorted(
        [(int(row["audio_id"]), row["reference_transcript"]) for row in rows]
    )
    parent = {sample_id: sample_id for sample_id, _ in items}

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(first: int, second: int) -> None:
        first_root, second_root = find(first), find(second)
        if first_root != second_root:
            parent[max(first_root, second_root)] = min(first_root, second_root)

    for index, (first_id, first_text) in enumerate(items):
        for second_id, second_text in items[index + 1 :]:
            if token_jaccard(first_text, second_text) >= threshold:
                union(first_id, second_id)
    roots = sorted({find(sample_id) for sample_id, _ in items})
    labels = {root: f"sc_{index:04d}" for index, root in enumerate(roots, start=1)}
    return {sample_id: labels[find(sample_id)] for sample_id, _ in items}


def grouped_split(
    rows: Iterable[dict],
    clusters: dict[int, str],
    *,
    dev_fraction: float,
    seed: int,
) -> dict[int, str]:
    """Assign complete semantic clusters to deterministic dev/test splits."""

    if not 0 < dev_fraction < 1:
        raise ValueError("dev_fraction must be in (0, 1)")
    groups: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        sample_id = int(row["audio_id"])
        groups[clusters[sample_id]].append(sample_id)
    ordered = sorted(groups.items())
    random.Random(seed).shuffle(ordered)
    target = round(sum(len(ids) for _, ids in ordered) * dev_fraction)
    dev_count = 0
    assignments = {}
    for _, ids in ordered:
        split = "dev" if dev_count < target else "test"
        for sample_id in ids:
            assignments[sample_id] = split
        if split == "dev":
            dev_count += len(ids)
    return assignments


def audit_leakage(
    rows: Iterable[dict],
    *,
    near_duplicate_threshold: float,
    prompt_examples: Iterable[str] = (),
) -> dict:
    """Audit base IDs and transcript similarity across declared splits."""

    items = list(rows)
    findings = {
        "same_base_id_cross_split": [],
        "exact_duplicate_cross_split": [],
        "normalized_duplicate_cross_split": [],
        "near_semantic_duplicate_cross_split": [],
        "same_augmentation_family_cross_split": [],
        "prompt_few_shot_overlap": [],
        "asset_pool_mismatch": [],
        "noise_hash_cross_split": [],
        "rir_hash_cross_split": [],
        "noise_recipe_hash_cross_split": [],
        "rir_recipe_hash_cross_split": [],
        "donor_split_mismatch": [],
        "target_in_noise_donors": [],
        "donor_semantic_cluster_overlap": [],
        "donor_audio_hash_cross_split": [],
        "crop_overlap_cross_split": [],
    }
    by_base: dict[int, set[str]] = defaultdict(set)
    by_family: dict[tuple[int, str], set[str]] = defaultdict(set)
    tracked_values: dict[str, dict[str, set[str]]] = {
        "noise_sha256": defaultdict(set),
        "rir_sha256": defaultdict(set),
        "noise_recipe_hash": defaultdict(set),
        "rir_recipe_hash": defaultdict(set),
    }
    donor_hash_splits: dict[str, set[str]] = defaultdict(set)
    crop_records: dict[str, list[dict]] = defaultdict(list)
    for row in items:
        base_id = int(row.get("base_id", row.get("audio_id")))
        split = str(row["split"])
        by_base[base_id].add(split)
        chain = row.get("augmentation_chain", [])
        family = "+".join(chain) if isinstance(chain, list) else str(chain)
        by_family[(base_id, family)].add(split)
        for pool_field in ("noise_split_pool", "rir_split_pool"):
            pool = row.get(pool_field)
            if pool is not None and str(pool) != split:
                findings["asset_pool_mismatch"].append(
                    {
                        "variant_id": row.get("variant_id"),
                        "field": pool_field,
                        "variant_split": split,
                        "asset_pool": pool,
                    }
                )
        for field, values in tracked_values.items():
            value = row.get(field)
            if value:
                values[str(value)].add(split)
        external_crop = row.get("noise_crop")
        noise_hash = row.get("noise_sha256")
        if external_crop and noise_hash:
            crop_records[str(noise_hash)].append(
                {
                    "variant_id": row.get("variant_id"),
                    "split": split,
                    "spans": external_crop.get("spans", []),
                }
            )
        for donor in row.get("noise_donor_crops", []):
            donor_id = int(donor["donor_base_id"])
            donor_split = str(donor["donor_split"])
            donor_hash = str(donor["source_audio_sha256"])
            donor_hash_splits[donor_hash].add(donor_split)
            if donor_split != split:
                findings["donor_split_mismatch"].append(
                    {
                        "variant_id": row.get("variant_id"),
                        "donor_base_id": donor_id,
                        "variant_split": split,
                        "donor_split": donor_split,
                    }
                )
            if donor_id == base_id:
                findings["target_in_noise_donors"].append(
                    {"variant_id": row.get("variant_id"), "base_id": base_id}
                )
            if donor.get("donor_semantic_cluster") == row.get("semantic_cluster"):
                findings["donor_semantic_cluster_overlap"].append(
                    {
                        "variant_id": row.get("variant_id"),
                        "base_id": base_id,
                        "donor_base_id": donor_id,
                        "semantic_cluster": row.get("semantic_cluster"),
                    }
                )
            crop_records[donor_hash].append(
                {
                    "variant_id": row.get("variant_id"),
                    "split": split,
                    "spans": donor.get("crop", {}).get("spans", []),
                }
            )
    findings["same_base_id_cross_split"] = [
        {"base_id": base_id, "splits": sorted(splits)}
        for base_id, splits in sorted(by_base.items())
        if len(splits) > 1
    ]
    findings["same_augmentation_family_cross_split"] = [
        {"base_id": base_id, "family": family, "splits": sorted(splits)}
        for (base_id, family), splits in sorted(by_family.items())
        if len(splits) > 1
    ]
    output_names = {
        "noise_sha256": "noise_hash_cross_split",
        "rir_sha256": "rir_hash_cross_split",
        "noise_recipe_hash": "noise_recipe_hash_cross_split",
        "rir_recipe_hash": "rir_recipe_hash_cross_split",
    }
    for field, values in tracked_values.items():
        findings[output_names[field]] = [
            {field: value, "splits": sorted(splits)}
            for value, splits in sorted(values.items())
            if len(splits) > 1
        ]
    findings["donor_audio_hash_cross_split"] = [
        {"source_audio_sha256": value, "splits": sorted(splits)}
        for value, splits in sorted(donor_hash_splits.items())
        if len(splits) > 1
    ]
    for source_hash, crops in sorted(crop_records.items()):
        for index, first in enumerate(crops):
            for second in crops[index + 1 :]:
                if first["split"] == second["split"]:
                    continue
                overlap = any(
                    max(int(a["source_start_sample"]), int(b["source_start_sample"]))
                    < min(int(a["source_end_sample"]), int(b["source_end_sample"]))
                    for a in first["spans"]
                    for b in second["spans"]
                )
                if overlap:
                    findings["crop_overlap_cross_split"].append(
                        {
                            "source_sha256": source_hash,
                            "variants": [first["variant_id"], second["variant_id"]],
                        }
                    )

    bases = {}
    for row in items:
        base_id = int(row.get("base_id", row.get("audio_id")))
        bases.setdefault(
            base_id,
            {
                "base_id": base_id,
                "split": str(row["split"]),
                "text": str(row.get("reference_transcript", "")),
            },
        )
    base_items = sorted(bases.values(), key=lambda row: row["base_id"])
    for index, first in enumerate(base_items):
        for second in base_items[index + 1 :]:
            if first["split"] == second["split"]:
                continue
            pair = [first["base_id"], second["base_id"]]
            if first["text"] == second["text"]:
                findings["exact_duplicate_cross_split"].append(pair)
            normalized_equal = normalize_text(first["text"]) == normalize_text(second["text"])
            if normalized_equal:
                findings["normalized_duplicate_cross_split"].append(pair)
            similarity = token_jaccard(first["text"], second["text"])
            if similarity >= near_duplicate_threshold and not normalized_equal:
                findings["near_semantic_duplicate_cross_split"].append(
                    {"base_ids": pair, "jaccard": similarity}
                )
    normalized_prompts = {normalize_text(value) for value in prompt_examples}
    findings["prompt_few_shot_overlap"] = [
        row["base_id"]
        for row in base_items
        if normalize_text(row["text"]) in normalized_prompts
    ]
    findings["leakage_detected"] = any(findings[key] for key in findings)
    return findings
