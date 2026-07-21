"""Plan or generate deterministic C0-C3 audio variants."""

from __future__ import annotations

import argparse
from collections import Counter
import csv
import json
import os
from pathlib import Path
import random
from typing import Iterable
import wave

from dataset_benchmark.robustness_v2.augmentation import (
    AudioData,
    audio_sha256,
    augment_file,
    config_hash,
    generate_image_source_rir,
    generate_procedural_noise,
    plan_crop,
    read_wav,
    stable_seed,
)
from dataset_benchmark.robustness_v2.split import grouped_split, semantic_clusters
from dataset_benchmark.scripts.common import (
    REPO_ROOT,
    json_safe,
    read_jsonl,
    resolve_path,
    sha256_file,
)


V2_ROOT = REPO_ROOT / "dataset_benchmark" / "robustness_v2"


def validate_output_paths(config: dict) -> None:
    """Reject any v2 write target outside the isolated v2 namespace."""

    for key in (
        "base_manifest_snapshot",
        "output_audio_dir",
        "planned_manifest",
        "generated_manifest",
        "leakage_audit_output",
    ):
        target = resolve_path(config[key]).resolve()
        try:
            target.relative_to(V2_ROOT.resolve())
        except ValueError as exc:
            raise ValueError(
                f"{key} must resolve under {V2_ROOT}; got {target}"
            ) from exc


def wav_info(path: Path) -> tuple[int, int]:
    with wave.open(str(path), "rb") as handle:
        return handle.getframerate(), handle.getnframes()


def read_manifest(path: Path) -> list[dict]:
    if path.suffix.casefold() == ".jsonl":
        return read_jsonl(path)
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if rows and "audio_id" not in rows[0]:
        raise ValueError(
            f"Base manifest must be UTF-8 comma-separated CSV or JSONL: {path}"
        )
    return rows


def write_variant_jsonl(path: Path, rows: Iterable[dict]) -> None:
    """Atomically write variant records without v1's audio_id assumption."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    ordered = sorted(
        rows, key=lambda row: (int(row["base_id"]), str(row["variant_id"]))
    )
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in ordered:
            handle.write(json.dumps(json_safe(row), ensure_ascii=False) + "\n")
    os.replace(temporary, path)


def write_base_snapshot_from_plan(plan_path: Path, target: Path) -> int:
    """Freeze one C0 row per base from a previously validated v2 plan."""

    plan_rows = read_jsonl(plan_path)
    c0_rows = [row for row in plan_rows if row.get("condition_level") == "C0"]
    by_base = {int(row["base_id"]): row for row in c0_rows}
    if len(by_base) != 130:
        raise ValueError(
            f"Expected 130 unique C0 bases in existing plan, found {len(by_base)}"
        )
    provenance_hash = sha256_file(plan_path)
    snapshot = []
    for base_id, row in sorted(by_base.items()):
        snapshot.append(
            {
                "audio_id": base_id,
                "audio_path": row["source_audio_path"],
                "speaker": row.get("speaker", ""),
                "reference_transcript": row["reference_transcript"],
                "eligibility_status": "eligible",
                "split": row.get("source_v1_split", row["split"]),
                "intent": row.get("intent", ""),
                "source_audio_sha256": row["source_audio_sha256"],
                "snapshot_source_plan_sha256": provenance_hash,
            }
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in snapshot:
            handle.write(json.dumps(json_safe(row), ensure_ascii=False) + "\n")
    os.replace(temporary, target)
    return len(snapshot)


def load_asset_manifest(path: Path | None, kind: str) -> list[dict]:
    if path is None or not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    required = {
        "asset_id",
        "category",
        "split_pool",
        "source_recording_id",
        "path",
        "license",
        "source",
    }
    if rows and not required.issubset(rows[0]):
        raise ValueError(f"{kind} manifest must contain {sorted(required)}")
    output = []
    for row in rows:
        asset_path = resolve_path(row["path"])
        output.append(
            {
                **row,
                "resolved_path": str(asset_path),
                "exists": asset_path.is_file(),
                "sha256": sha256_file(asset_path) if asset_path.is_file() else None,
            }
        )
    return output


def validate_asset_pools(assets: list[dict], kind: str) -> None:
    """Reject pool mismatches and disguised duplicate files across splits."""

    by_hash: dict[str, set[str]] = {}
    for row in assets:
        if row["split_pool"] not in {"dev", "test"}:
            raise ValueError(
                f"{kind} asset {row['asset_id']} has invalid split_pool: "
                f"{row['split_pool']}"
            )
        if row.get("sha256"):
            by_hash.setdefault(row["sha256"], set()).add(row["split_pool"])
    leaked = {digest: pools for digest, pools in by_hash.items() if len(pools) > 1}
    if leaked:
        raise ValueError(
            f"{kind} asset hashes occur in multiple split pools: "
            + ", ".join(sorted(leaked))
        )


def _choose(rng, values: list, default=None):
    return values[rng.randrange(len(values))] if values else default


def _resolve_operations(chain: dict, rng) -> list[dict]:
    operations = []
    for source in chain.get("operations", []):
        operation = dict(source)
        for key in list(operation):
            if key.endswith("_choices"):
                target = key[: -len("_choices")]
                operation[target] = _choose(rng, list(operation.pop(key)))
        operations.append(operation)
    return operations


def _asset_for_category(
    assets: list[dict], category: str | None, split_pool: str, rng
) -> dict | None:
    candidates = [
        row
        for row in assets
        if (not category or row["category"] == category)
        and row["split_pool"] == split_pool
    ]
    return candidates[rng.randrange(len(candidates))] if candidates else None


def _json_hash(payload: dict) -> str:
    return config_hash(payload)


def _procedural_parameters(operation: dict, rng: random.Random) -> dict:
    generator = operation.get("generator")
    if generator == "synthetic_fan_proxy":
        return {
            "color": operation.get("color", "pink"),
            "fundamental_hz": float(operation.get("fundamental_hz", 50.0)),
            "harmonics": int(operation.get("harmonics", 5)),
            "modulation_hz": round(rng.uniform(0.25, 0.7), 6),
            "modulation_depth": float(operation.get("modulation_depth", 0.12)),
        }
    if generator == "synthetic_office_proxy":
        return {
            "color": operation.get("color", "pink"),
            "click_rate_hz": float(operation.get("click_rate_hz", 1.5)),
        }
    if generator in {"in_corpus_speech_babble", "synthetic_cafe_proxy"}:
        return {"donor_count": int(operation.get("donor_count", 4))}
    return {}


def _synthetic_rir_parameters(operation: dict, rng: random.Random) -> dict:
    ranges = operation.get(
        "room_dimension_ranges_m", [[3.0, 6.0], [3.0, 5.0], [2.5, 3.5]]
    )
    room = [round(rng.uniform(float(low), float(high)), 6) for low, high in ranges]

    def position() -> list[float]:
        return [round(rng.uniform(0.5, dimension - 0.5), 6) for dimension in room]

    return {
        "room_dimensions_m": room,
        "source_position_m": position(),
        "microphone_position_m": position(),
        "rt60_sec": float(operation.get("rt60_sec", 0.4)),
        "duration_sec": float(operation.get("duration_sec", 0.6)),
        "max_order": int(operation.get("max_order", 6)),
        "speed_of_sound_mps": 343.0,
    }


def plan_variants(config: dict, manifest_rows: Iterable[dict]) -> list[dict]:
    """Build a deterministic, fully hashed augmentation plan."""

    eligible = [row for row in manifest_rows if row["eligibility_status"] == "eligible"]
    procedural_config = config.get("procedural_generation", {})
    generator_version = procedural_config.get("version", "external_asset_v1")
    evidence_tier = procedural_config.get(
        "evidence_tier", "controlled_external_or_synthetic"
    )
    real_world_claim_allowed = procedural_config.get(
        "real_world_generalization_claim_allowed", False
    )
    external_validation_status = procedural_config.get(
        "external_validation_status", "not_specified"
    )
    split_config = config["split"]
    clusters = semantic_clusters(
        eligible, float(split_config["near_duplicate_jaccard_threshold"])
    )
    split_assignments = None
    if split_config.get("strategy") == "semantic_cluster_v2_research":
        split_assignments = grouped_split(
            eligible,
            clusters,
            dev_fraction=float(split_config["dev_fraction"]),
            seed=int(split_config["seed"]),
        )
    base_metadata = {}
    for row in eligible:
        base_id = int(row["audio_id"])
        # Snapshot manifests preserve the original absolute path for provenance.
        # If that path is stale after clone, relocate its repository-relative
        # suffix without rewriting the frozen snapshot or changing its hash.
        recorded_path = Path(str(row["audio_path"]))
        path = resolve_path(recorded_path)
        if not path.exists() and recorded_path.is_absolute():
            lowered = [part.casefold() for part in recorded_path.parts]
            if "dataset_benchmark" in lowered:
                index = lowered.index("dataset_benchmark")
                path = resolve_path(Path(*recorded_path.parts[index:]))
        sample_rate, frames = wav_info(path)
        base_metadata[base_id] = {
            "base_id": base_id,
            "path": path,
            "sha256": sha256_file(path),
            "sample_rate": sample_rate,
            "frames": frames,
            "split": (
                split_assignments[base_id]
                if split_assignments is not None
                else row["split"]
            ),
            "semantic_cluster": clusters[base_id],
        }
    noise_assets = load_asset_manifest(
        resolve_path(config["noise_asset_manifest"])
        if config.get("noise_asset_manifest")
        else None,
        "noise",
    )
    rir_assets = load_asset_manifest(
        resolve_path(config["rir_asset_manifest"])
        if config.get("rir_asset_manifest")
        else None,
        "RIR",
    )
    validate_asset_pools(noise_assets, "noise")
    validate_asset_pools(rir_assets, "RIR")
    experiment_hash = config_hash(config)
    output_root = resolve_path(config["output_audio_dir"])
    records = []
    for row in sorted(eligible, key=lambda item: int(item["audio_id"])):
        base_id = int(row["audio_id"])
        base = base_metadata[base_id]
        source_path = base["path"]
        source_hash = base["sha256"]
        source_sample_rate = base["sample_rate"]
        target_split = base["split"]
        for condition, condition_config in config["conditions"].items():
            if not condition_config.get("enabled", True):
                continue
            variants = int(condition_config["variants_per_base"])
            chains = condition_config.get("chains", [{"id": "original", "operations": []}])
            for variant_index in range(variants):
                seed = stable_seed(
                    config["global_seed"],
                    "variant",
                    target_split,
                    base_id,
                    condition,
                    variant_index,
                )
                rng = random.Random(seed)
                chain = chains[variant_index % len(chains)]
                operations = _resolve_operations(chain, rng)
                operation_names = [item["name"] for item in operations]
                noise_operation = next(
                    (item for item in operations if item["name"] == "background_noise"),
                    None,
                )
                rir_operation = next(
                    (item for item in operations if item["name"] == "room_reverberation"),
                    None,
                )
                noise_type = noise_operation.get("noise_type") if noise_operation else None
                noise_generator = (
                    noise_operation.get("generator", "external_asset")
                    if noise_operation
                    else None
                )
                rir_generator = (
                    rir_operation.get("generator", "external_asset")
                    if rir_operation
                    else None
                )
                noise_seed = (
                    stable_seed(config["global_seed"], "noise", target_split, base_id, condition, variant_index)
                    if noise_operation
                    else None
                )
                rir_seed = (
                    stable_seed(config["global_seed"], "rir", target_split, base_id, condition, variant_index)
                    if rir_operation
                    else None
                )
                noise_rng = random.Random(noise_seed) if noise_seed is not None else None
                rir_rng = random.Random(rir_seed) if rir_seed is not None else None
                noise = None
                rir = None
                noise_crop = None
                noise_donor_crops = []
                noise_recipe = None
                rir_recipe = None
                missing = []
                if noise_operation and noise_generator == "external_asset":
                    assert noise_rng is not None
                    noise = _asset_for_category(
                        noise_assets, noise_type, target_split, noise_rng
                    )
                    if noise is None or not noise["exists"]:
                        missing.append(f"noise:{noise_type}:{target_split}")
                    else:
                        asset_rate, asset_frames = wav_info(Path(noise["resolved_path"]))
                        resampled_frames = round(
                            asset_frames * source_sample_rate / asset_rate
                        )
                        noise_crop = plan_crop(
                            resampled_frames, base["frames"], noise_rng
                        )
                        noise_operation["asset_crop"] = noise_crop
                        noise_recipe = {
                            "mode": "external_asset",
                            "split_pool": target_split,
                            "asset_id": noise["asset_id"],
                            "source_recording_id": noise["source_recording_id"],
                            "asset_sha256": noise["sha256"],
                            "crop": noise_crop,
                        }
                elif noise_operation:
                    assert noise_rng is not None and noise_seed is not None
                    parameters = _procedural_parameters(noise_operation, noise_rng)
                    donor_count = int(parameters.get("donor_count", 0))
                    if donor_count:
                        candidates = [
                            item
                            for item in base_metadata.values()
                            if item["split"] == target_split
                            and item["base_id"] != base_id
                            and item["semantic_cluster"] != base["semantic_cluster"]
                        ]
                        if len(candidates) < donor_count:
                            raise ValueError(
                                f"Not enough {target_split} donors for {base_id}: "
                                f"need {donor_count}, found {len(candidates)}"
                            )
                        for donor in noise_rng.sample(candidates, donor_count):
                            resampled_frames = round(
                                donor["frames"]
                                * source_sample_rate
                                / donor["sample_rate"]
                            )
                            crop = plan_crop(
                                resampled_frames, base["frames"], noise_rng
                            )
                            noise_donor_crops.append(
                                {
                                    "donor_base_id": donor["base_id"],
                                    "donor_split": donor["split"],
                                    "donor_semantic_cluster": donor["semantic_cluster"],
                                    "source_audio_path": str(donor["path"]),
                                    "source_audio_sha256": donor["sha256"],
                                    "source_sample_rate": donor["sample_rate"],
                                    "resampled_sample_rate": source_sample_rate,
                                    "crop": crop,
                                    "gain": round(noise_rng.uniform(0.7, 1.0), 6),
                                }
                            )
                    noise_recipe = {
                        "mode": "procedural",
                        "generator": noise_generator,
                        "generator_version": generator_version,
                        "split_pool": target_split,
                        "seed": noise_seed,
                        "target_samples": base["frames"],
                        "sample_rate": source_sample_rate,
                        "parameters": parameters,
                        "donors": noise_donor_crops,
                    }
                if rir_operation and rir_generator == "external_asset":
                    assert rir_rng is not None
                    rir = _asset_for_category(rir_assets, None, target_split, rir_rng)
                    if rir is None or not rir["exists"]:
                        missing.append(f"rir:{target_split}")
                    else:
                        rir_recipe = {
                            "mode": "external_asset",
                            "split_pool": target_split,
                            "asset_id": rir["asset_id"],
                            "source_recording_id": rir["source_recording_id"],
                            "asset_sha256": rir["sha256"],
                        }
                elif rir_operation:
                    assert rir_rng is not None and rir_seed is not None
                    parameters = _synthetic_rir_parameters(rir_operation, rir_rng)
                    rir_recipe = {
                        "mode": "procedural",
                        "generator": "synthetic_image_source",
                        "generator_version": generator_version,
                        "split_pool": target_split,
                        "seed": rir_seed,
                        "sample_rate": source_sample_rate,
                        "parameters": parameters,
                    }
                variant_id = f"{base_id}_{condition.lower()}_v{variant_index + 1:02d}_{chain['id']}"
                output_path = output_root / condition / f"{variant_id}.wav"
                snr_db = next(
                    (item.get("snr_db") for item in operations if item["name"] == "background_noise"),
                    None,
                )
                speed_factor = next(
                    (item.get("factor") for item in operations if item["name"].startswith("speed")),
                    1.0,
                )
                records.append(
                    {
                        "schema_version": "2.0.0",
                        "evidence_tier": evidence_tier,
                        "real_world_generalization_claim_allowed": real_world_claim_allowed,
                        "external_validation_status": external_validation_status,
                        "base_id": base_id,
                        "variant_id": variant_id,
                        "speaker": row.get("speaker", ""),
                        "condition_level": condition,
                        "augmentation_chain": operation_names,
                        "augmentation_parameters": operations,
                        "noise_type": noise_type,
                        "noise_mode": noise_recipe.get("mode") if noise_recipe else None,
                        "noise_generator": noise_generator,
                        "noise_split_pool": target_split if noise_operation else None,
                        "noise_asset_id": noise.get("asset_id") if noise else None,
                        "noise_source_recording_id": (
                            noise.get("source_recording_id") if noise else None
                        ),
                        "noise_crop": noise_crop,
                        "noise_donor_crops": noise_donor_crops,
                        "noise_recipe": noise_recipe,
                        "noise_recipe_hash": _json_hash(noise_recipe) if noise_recipe else None,
                        "snr_db": snr_db,
                        "rir_id": (
                            rir.get("asset_id")
                            if rir
                            else f"{target_split}_synthetic_rir_{rir_seed:08x}"
                            if rir_recipe
                            else None
                        ),
                        "rir_mode": rir_recipe.get("mode") if rir_recipe else None,
                        "rir_generator": rir_generator,
                        "rir_split_pool": target_split if rir_operation else None,
                        "rir_source_recording_id": (
                            rir.get("source_recording_id") if rir else None
                        ),
                        "rir_recipe": rir_recipe,
                        "rir_recipe_hash": _json_hash(rir_recipe) if rir_recipe else None,
                        "codec": "mulaw_proxy" if "codec_compression" in operation_names else None,
                        "sample_rate": source_sample_rate,
                        "speed_factor": speed_factor,
                        "seed": seed,
                        "source_audio_path": str(source_path),
                        "output_audio_path": str(source_path if condition == "C0" else output_path),
                        "source_audio_sha256": source_hash,
                        "noise_path": noise.get("resolved_path") if noise else None,
                        "noise_sha256": noise.get("sha256") if noise else None,
                        "rir_path": rir.get("resolved_path") if rir else None,
                        "rir_sha256": rir.get("sha256") if rir else None,
                        "output_audio_sha256": source_hash if condition == "C0" else None,
                        "augmentation_config_hash": experiment_hash,
                        "split": target_split,
                        "source_v1_split": row["split"],
                        "semantic_cluster": clusters[base_id],
                        "intent": row.get("intent", ""),
                        "reference_transcript": row["reference_transcript"],
                        "missing_assets": missing,
                        "status": "ready" if not missing else "blocked_missing_asset",
                    }
                )
    return records


def dry_run_summary(records: list[dict]) -> dict:
    variant_ids = [row["variant_id"] for row in records]
    duplicate_ids = sorted(
        variant_id for variant_id, count in Counter(variant_ids).items() if count > 1
    )
    missing = Counter(
        asset for row in records for asset in row.get("missing_assets", [])
    )
    source_sizes = {}
    for row in records:
        source_sizes.setdefault(row["base_id"], Path(row["source_audio_path"]).stat().st_size)
    estimated_bytes = sum(
        source_sizes[row["base_id"]] / max(float(row.get("speed_factor") or 1.0), 0.01)
        for row in records
        if row["condition_level"] != "C0"
    )
    first = records[0] if records else {}
    return {
        "base_samples": len({row["base_id"] for row in records}),
        "planned_variants": len(records),
        "estimated_generated_bytes": round(estimated_bytes),
        "estimated_generated_mib": round(estimated_bytes / (1024**2), 2),
        "condition_distribution": dict(sorted(Counter(row["condition_level"] for row in records).items())),
        "speaker_distribution": dict(sorted(Counter(row["speaker"] for row in records).items())),
        "split_distribution": dict(sorted(Counter(row["split"] for row in records).items())),
        "missing_assets": dict(sorted(missing.items())),
        "duplicate_variant_ids": duplicate_ids,
        "noise_mode_distribution": dict(
            sorted(Counter(row.get("noise_mode") or "none" for row in records).items())
        ),
        "noise_generator_distribution": dict(
            sorted(
                Counter(row.get("noise_generator") or "none" for row in records).items()
            )
        ),
        "rir_mode_distribution": dict(
            sorted(Counter(row.get("rir_mode") or "none" for row in records).items())
        ),
        "speech_donor_references": sum(
            len(row.get("noise_donor_crops", [])) for row in records
        ),
        "evidence_tier": first.get("evidence_tier"),
        "real_world_generalization_claim_allowed": first.get(
            "real_world_generalization_claim_allowed"
        ),
        "augmentation_config_hash": first.get("augmentation_config_hash"),
    }


def generate(records: list[dict], *, condition: str | None = None) -> list[dict]:
    output = []
    for original in records:
        row = dict(original)
        if condition and row["condition_level"] != condition:
            continue
        if row["condition_level"] == "C0":
            row["status"] = "success"
            output.append(row)
            continue
        if row["missing_assets"]:
            output.append(row)
            continue
        noise_audio = None
        noise_recipe = row.get("noise_recipe") or {}
        if noise_recipe.get("mode") == "procedural":
            donor_tracks = [
                (
                    read_wav(Path(donor["source_audio_path"])),
                    donor["crop"],
                    float(donor["gain"]),
                )
                for donor in noise_recipe.get("donors", [])
            ]
            noise_audio = generate_procedural_noise(
                noise_recipe["generator"],
                int(noise_recipe["target_samples"]),
                int(noise_recipe["sample_rate"]),
                seed=int(noise_recipe["seed"]),
                parameters=noise_recipe["parameters"],
                donor_tracks=donor_tracks,
            )
            row["planned_noise_sha256"] = audio_sha256(noise_audio)
        rir_audio = None
        rir_recipe = row.get("rir_recipe") or {}
        if rir_recipe.get("mode") == "procedural":
            rir_audio = generate_image_source_rir(
                int(rir_recipe["sample_rate"]),
                parameters=rir_recipe["parameters"],
            )
            row["planned_rir_sha256"] = audio_sha256(rir_audio)
        metadata = augment_file(
            Path(row["source_audio_path"]),
            Path(row["output_audio_path"]),
            row["augmentation_parameters"],
            seed=int(row["seed"]),
            noise_path=Path(row["noise_path"]) if row.get("noise_path") else None,
            rir_path=Path(row["rir_path"]) if row.get("rir_path") else None,
            noise_audio=noise_audio,
            rir_audio=rir_audio,
        )
        row.update(metadata)
        row["status"] = "success"
        output.append(row)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="dataset_benchmark/robustness_v2/configs/augmentation_config.json",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--plan-manifest", action="store_true")
    parser.add_argument("--snapshot-from-existing-plan", action="store_true")
    parser.add_argument("--condition", choices=("C0", "C1", "C2", "C3"))
    args = parser.parse_args()
    config = json.loads(resolve_path(args.config).read_text(encoding="utf-8"))
    validate_output_paths(config)
    if args.snapshot_from_existing_plan:
        count = write_base_snapshot_from_plan(
            resolve_path(config["planned_manifest"]),
            resolve_path(config["base_manifest_snapshot"]),
        )
        print(f"Wrote {count} base rows to {resolve_path(config['base_manifest_snapshot'])}")
        return
    records = plan_variants(config, read_manifest(resolve_path(config["base_manifest"])))
    summary = dry_run_summary(records)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if args.dry_run:
        return
    if args.plan_manifest:
        write_variant_jsonl(resolve_path(config["planned_manifest"]), records)
        print(resolve_path(config["planned_manifest"]))
        return
    generated = generate(records, condition=args.condition)
    write_variant_jsonl(resolve_path(config["generated_manifest"]), generated)
    print(resolve_path(config["generated_manifest"]))


if __name__ == "__main__":
    main()
