"""Generate the deterministic controlled text-diagnostic manifest."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
from typing import Iterable, Mapping

from dataset_benchmark.robustness_v2.error_analysis import build_stage_metadata
from dataset_benchmark.robustness_v2.pipeline import canonical_hash
from dataset_benchmark.robustness_v2.text_diagnostics import apply_corruption
from dataset_benchmark.scripts.common import atomic_write_json, read_jsonl, resolve_path, sha256_file


def write_jsonl(path: Path, rows: Iterable[Mapping]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n")
    temporary.replace(path)


def generate(config: dict, config_path: Path, *, dry_run: bool = False) -> dict:
    source_path = resolve_path(config["source_manifest"])
    source_rows = read_jsonl(source_path)
    source_hash = sha256_file(source_path)
    generated: list[dict] = []
    base_seed = int(config["seed"])
    for source_index, source in enumerate(sorted(source_rows, key=lambda row: int(row["audio_id"]))):
        reference = source["reference_transcript"]
        for corruption_index, kind in enumerate(config["corruptions"]):
            for severity in config["severities"]:
                seed = base_seed + source_index * 1000 + corruption_index * 10 + int(severity)
                result = apply_corruption(reference, kind, int(severity), seed)
                generated.append(
                    {
                        "schema_version": config["schema_version"],
                        "diagnostic_id": f"{source['audio_id']}_{kind}_s{severity}",
                        "base_id": int(source["audio_id"]),
                        "split": source.get("split"),
                        "intent": source.get("intent"),
                        "reference_text": reference,
                        "corrupted_text": result.text,
                        "corruption_type": kind,
                        "severity": int(severity),
                        "seed": seed,
                        "status": "generated" if result.applied else "excluded",
                        "exclusion_reason": result.exclusion_reason,
                        "corruption_metadata": result.metadata,
                        "source_manifest_sha256": source_hash,
                        "meaning_contract": "reference_text remains the intended gold meaning",
                    }
                )
    status_counts = Counter(row["status"] for row in generated)
    type_counts = Counter(
        (row["corruption_type"], row["status"])
        for row in generated
    )
    summary = {
        "schema_version": config["schema_version"],
        "config_hash": canonical_hash(config),
        "source_rows": len(source_rows),
        "planned_rows": len(generated),
        "status_counts": dict(status_counts),
        "counts_by_type_and_status": {
            f"{kind}:{status}": count for (kind, status), count in sorted(type_counts.items())
        },
        "disclosure": config["disclosure"],
        "writes_performed": not dry_run,
    }
    if dry_run:
        return summary
    manifest_path = resolve_path(config["outputs"]["manifest"])
    summary_path = resolve_path(config["outputs"]["summary"])
    metadata_path = resolve_path(config["outputs"]["metadata"])
    write_jsonl(manifest_path, generated)
    summary["manifest_sha256"] = sha256_file(manifest_path)
    atomic_write_json(summary_path, summary)
    metadata = build_stage_metadata(
        "generate_text_diagnostics",
        inputs={"config": config_path, "source_manifest": source_path},
        outputs={"manifest": manifest_path, "summary": summary_path},
        details={"config_hash": canonical_hash(config), "api_calls": 0},
    )
    atomic_write_json(metadata_path, metadata)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="dataset_benchmark/robustness_v2/configs/text_diagnostics_config.json",
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config_path = resolve_path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    print(json.dumps(generate(config, config_path, dry_run=args.dry_run), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
