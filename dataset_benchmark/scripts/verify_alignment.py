from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import json
from pathlib import Path
import random

try:
    from .common import (
        atomic_write_jsonl,
        load_config,
        read_jsonl,
        resolve_path,
        sha256_file,
        sha256_text,
    )
    from .metrics import transcript_errors
except ImportError:
    from common import (
        atomic_write_jsonl,
        load_config,
        read_jsonl,
        resolve_path,
        sha256_file,
        sha256_text,
    )
    from metrics import transcript_errors


def read_manifest(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def select_crosscheck_rows(
    rows: list[dict], *, start_id: int, end_id: int, count: int, seed: int
) -> list[dict]:
    candidates = [
        row
        for row in rows
        if start_id <= int(row["audio_id"]) <= end_id
        and row["audio_path"]
        and row["reference_transcript"]
    ]
    if count > len(candidates):
        raise ValueError(f"Requested {count} samples from only {len(candidates)} candidates")

    duration_order = sorted(
        candidates, key=lambda row: (float(row["duration_sec"]), int(row["audio_id"]))
    )
    quartile = {
        int(row["audio_id"]): min(3, index * 4 // len(duration_order)) + 1
        for index, row in enumerate(duration_order)
    }
    groups: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for row in candidates:
        groups[(row["speaker"], quartile[int(row["audio_id"])])].append(row)

    rng = random.Random(seed)
    selected: list[dict] = []
    minimum_per_stratum = count // len(groups)
    for key in sorted(groups):
        items = list(groups[key])
        rng.shuffle(items)
        selected.extend(items[:minimum_per_stratum])
    remaining = [row for row in candidates if row not in selected]
    rng.shuffle(remaining)
    selected.extend(remaining[: count - len(selected)])

    for row in selected:
        row["validation_duration_quartile"] = quartile[int(row["audio_id"])]
    return sorted(selected, key=lambda row: int(row["audio_id"]))


def print_results(rows: list[dict]) -> None:
    print("\n=== ALIGNMENT CROSS-CHECK ===")
    for row in rows:
        print(
            f"\nID {row['audio_id']} | {row['speaker']} | "
            f"q{row['duration_quartile']} | WER={row['wer']:.3f}"
        )
        print("REF:", row["reference_transcript"])
        print("STT:", row["stt_transcript"])
    successful = [row for row in rows if row["status"] == "success"]
    summary = {
        "samples": len(rows),
        "successful": len(successful),
        "exact_normalized": sum(row["word_errors"] == 0 for row in successful),
        "wer_lt_0_5": sum(row["wer"] < 0.5 for row in successful),
        "wer_ge_1": sum(row["wer"] >= 1 for row in successful),
        "mean_wer": (
            sum(row["wer"] for row in successful) / len(successful)
            if successful
            else None
        ),
    }
    print("\nSUMMARY", json.dumps(summary, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="dataset_benchmark/benchmark_config.json")
    parser.add_argument("--start-id", type=int, default=101)
    parser.add_argument("--end-id", type=int, default=230)
    parser.add_argument("--count", type=int, default=20)
    parser.add_argument("--seed", type=int, default=44)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    selected = select_crosscheck_rows(
        read_manifest(resolve_path(config["manifest"])),
        start_id=args.start_id,
        end_id=args.end_id,
        count=args.count,
        seed=args.seed,
    )
    print("SELECTED_IDS", [int(row["audio_id"]) for row in selected])
    print(
        "STRATA",
        [
            (
                int(row["audio_id"]),
                row["speaker"],
                row["validation_duration_quartile"],
            )
            for row in selected
        ],
    )
    if args.dry_run:
        return

    from app.services.stt_service import STT_PROMPT, speech_to_text

    output = (
        resolve_path(config["output_dir"])
        / f"alignment_check_{args.start_id}_{args.end_id}.jsonl"
    )
    cache = {
        int(row["audio_id"]): row for row in read_jsonl(output)
    } if args.resume else {}
    for index, manifest in enumerate(selected, start=1):
        audio_id = int(manifest["audio_id"])
        audio_path = resolve_path(manifest["audio_path"])
        input_hash = sha256_text(
            "|".join(
                [
                    sha256_file(audio_path),
                    "gpt-4o-mini-transcribe",
                    "whisper-1",
                    STT_PROMPT,
                ]
            )
        )
        cached = cache.get(audio_id, {})
        if not (
            cached.get("input_sha256") == input_hash
            and cached.get("status") == "success"
        ):
            transcript = speech_to_text(audio_path.read_bytes(), audio_path.name)
            errors = transcript_errors(manifest["reference_transcript"], transcript)
            cache[audio_id] = {
                "audio_id": audio_id,
                "speaker": manifest["speaker"],
                "duration_quartile": manifest["validation_duration_quartile"],
                "audio_sha256": sha256_file(audio_path),
                "input_sha256": input_hash,
                "reference_transcript": manifest["reference_transcript"],
                "stt_transcript": transcript,
                "status": "success" if transcript else "failed",
                **errors,
            }
            atomic_write_jsonl(output, cache.values())
        print(
            f"[{index:02d}/{len(selected)}] ID={audio_id} "
            f"status={cache[audio_id]['status']}"
        )
    print_results([cache[int(row["audio_id"])] for row in selected])


if __name__ == "__main__":
    main()
