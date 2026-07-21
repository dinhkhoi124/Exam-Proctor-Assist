"""One-command, provenance-safe P0/P1/P2 robustness pilot runner."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from time import perf_counter, sleep
from typing import Any, Callable, Iterable, Mapping
import wave

from dataset_benchmark.robustness_v2.error_analysis import build_stage_metadata
from dataset_benchmark.robustness_v2.scripts.evaluate_robustness import evaluate
from dataset_benchmark.robustness_v2.scripts.generate_robustness_report import generate
from dataset_benchmark.robustness_v2.pipeline import (
    PIPELINES,
    HeuristicCorrectionRiskDetector,
    RiskDetectorInput,
    answer_cache_key,
    canonical_hash,
    correction_cache_key,
    correction_requirements,
    retrieval_cache_key,
    risk_cache_key,
    select_pipeline_transcript,
    stt_cache_key,
)
from dataset_benchmark.scripts.common import (
    atomic_write_json,
    read_jsonl,
    resolve_path,
    sha256_file,
    sha256_text,
)


PRIORITY3_STAGES = (
    "validate_config",
    "build_manifest",
    "generate_augmentation",
    "stt",
    "risk_detection",
    "correction",
    "retrieval",
    "final_answers",
)
PRIORITY4_STAGES = ("judge", "evaluate", "report")


def replace_with_retry(
    temporary: Path,
    target: Path,
    *,
    attempts: int = 8,
    base_delay_seconds: float = 0.05,
) -> None:
    """Atomically replace a file, retrying transient Windows sharing violations."""

    for attempt in range(attempts):
        try:
            os.replace(temporary, target)
            return
        except PermissionError:
            if attempt + 1 >= attempts:
                raise
            sleep(min(base_delay_seconds * (2**attempt), 2.0))


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    """Atomically write records with stable cache-id ordering."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + ".tmp")
    ordered = sorted(
        (dict(row) for row in rows),
        key=lambda row: str(row.get("cache_id") or row.get("variant_id") or ""),
    )
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in ordered:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    replace_with_retry(temporary, target)


def variant_audio_path(config: Mapping[str, Any], row: Mapping[str, Any]) -> Path:
    """Resolve a manifest audio path, relocating stale absolute paths after clone."""

    recorded = Path(str(row["output_audio_path"]))
    if recorded.exists():
        return recorded

    if recorded.is_absolute():
        lowered = [part.casefold() for part in recorded.parts]
        if "dataset_benchmark" in lowered:
            index = lowered.index("dataset_benchmark")
            relocated = resolve_path(Path(*recorded.parts[index:]))
            if relocated.exists():
                return relocated

    augmentation_path = resolve_path(config["dataset"]["augmentation_config"])
    augmentation = json.loads(augmentation_path.read_text(encoding="utf-8"))
    if row.get("condition_level") == "C0":
        return recorded
    else:
        candidate = (
            resolve_path(augmentation["output_audio_dir"])
            / str(row["condition_level"])
            / recorded.name
        )
    return candidate if candidate.exists() else recorded


def clean_retrieval(result: Mapping[str, Any], *, signal_only: bool = False) -> dict:
    """Remove images and optionally large text fields from retrieval output."""

    candidates = []
    for item in result.get("candidates", []):
        cleaned = {
            key: value
            for key, value in item.items()
            if key not in {"image_base64", "base64"}
        }
        if signal_only:
            cleaned = {
                key: cleaned.get(key)
                for key in ("source", "page", "combined_score", "rank")
            }
        candidates.append(cleaned)
    final_pages = [] if signal_only else [
        {
            key: value
            for key, value in item.items()
            if key not in {"image_base64", "base64"}
        }
        for item in result.get("final_pages", [])
    ]
    return {
        "status": result.get("status"),
        "candidates": candidates,
        "final_pages": final_pages,
    }


def _deep_merge(base: Mapping[str, Any], override: Mapping[str, Any]) -> dict:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: Path) -> dict:
    """Load a config, optionally merging a small local handoff override."""

    raw = json.loads(path.read_text(encoding="utf-8"))
    parent = raw.pop("extends", None)
    if not parent:
        return raw
    parent_path = resolve_path(parent)
    return _deep_merge(load_config(parent_path), raw)


def require_paid_api_confirmation(config: Mapping[str, Any]) -> None:
    execution = config.get("execution", {})
    if not execution.get("requires_paid_api_confirmation", False):
        return
    variable = str(execution["confirmation_env_var"])
    expected = str(execution["confirmation_value"])
    if os.getenv(variable) != expected:
        raise RuntimeError(
            f"Paid API gate is closed. Review --dry-run cost, then set {variable} "
            "to the exact confirmation value documented in LOCAL_INFERENCE_RUNBOOK.md."
        )


def cache_path(config: Mapping[str, Any], name: str) -> Path:
    return resolve_path(config["outputs"]["cache_dir"]) / f"{name}.jsonl"


def checkpoint_path(config: Mapping[str, Any], stage: str) -> Path:
    return resolve_path(config["outputs"]["checkpoint_dir"]) / f"{stage}.metadata.json"


def index_signature(config: Mapping[str, Any]) -> tuple[str, list[Path]]:
    vector_dir = resolve_path(config["retrieval"]["vector_store_dir"])
    files = [
        vector_dir / name
        for name in ("index.faiss", "metadata.json", "bm25.pkl", "bm25_corpus.json")
        if (vector_dir / name).exists()
    ]
    return (
        sha256_text("|".join(f"{path.name}:{sha256_file(path)}" for path in files)),
        files,
    )


def selected_variants(config: Mapping[str, Any], args: argparse.Namespace) -> list[dict]:
    rows = read_jsonl(resolve_path(config["dataset"]["variant_manifest"]))
    condition = args.condition if args.condition is not None else config["dataset"].get("default_condition")
    if condition:
        rows = [row for row in rows if row["condition_level"] == condition]
    if args.base_id:
        requested = set(args.base_id)
        rows = [row for row in rows if int(row["base_id"]) in requested]
    unique_base = []
    seen = set()
    for row in sorted(rows, key=lambda item: (int(item["base_id"]), item["variant_id"])):
        base_id = int(row["base_id"])
        if base_id not in seen:
            seen.add(base_id)
            unique_base.append(base_id)
    configured_limit = config["dataset"].get(
        "default_base_limit", config["dataset"].get("pilot_max_base")
    )
    limit = args.limit if args.limit is not None else configured_limit
    maximum = int(config["dataset"].get("maximum_base", config["dataset"]["pilot_max_base"]))
    if limit is not None and int(limit) > maximum:
        raise ValueError(f"--limit must be <= configured maximum_base ({maximum})")
    if limit is None:
        return rows
    limit = int(limit)
    allowed = set(unique_base[:limit])
    return [row for row in rows if int(row["base_id"]) in allowed]


def selected_pipelines(config: Mapping[str, Any], args: argparse.Namespace) -> tuple[str, ...]:
    requested = args.pipeline or list(config["pipelines"])
    values = tuple(dict.fromkeys(requested))
    invalid = set(values) - set(PIPELINES)
    if invalid:
        raise ValueError(f"Unknown pipelines: {sorted(invalid)}")
    return values


def validate_config(config: Mapping[str, Any], config_path: Path) -> dict:
    required_paths = {
        "config": config_path,
        "base_manifest": resolve_path(config["dataset"]["base_manifest"]),
        "variant_manifest": resolve_path(config["dataset"]["variant_manifest"]),
        "augmentation_plan": resolve_path(config["dataset"]["augmentation_plan"]),
        "split_audit": resolve_path(config["dataset"]["split_audit"]),
        "correction_prompt": resolve_path(config["correction"]["prompt_path"]),
        "answer_prompt": resolve_path(config["answer_generation"]["prompt_path"]),
    }
    if config.get("judge", {}).get("enabled", False):
        required_paths["judge_prompt"] = resolve_path(config["judge"]["prompt_path"])
    missing = [name for name, path in required_paths.items() if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required inputs: {missing}")
    prompt_checks = {
        "correction": (
            sha256_file(required_paths["correction_prompt"]),
            config["correction"]["prompt_sha256"],
        ),
        "answer": (
            sha256_file(required_paths["answer_prompt"]),
            config["answer_generation"]["prompt_sha256"],
        ),
    }
    if config.get("judge", {}).get("enabled", False):
        prompt_checks["judge"] = (
            sha256_file(required_paths["judge_prompt"]),
            config["judge"]["prompt_sha256"],
        )
    mismatches = [name for name, pair in prompt_checks.items() if pair[0] != pair[1]]
    if mismatches:
        raise ValueError(f"Prompt lock mismatch: {mismatches}")
    split_audit = json.loads(required_paths["split_audit"].read_text(encoding="utf-8"))
    if split_audit.get("leakage_detected"):
        raise ValueError("Split leakage audit is not clean")
    v2_root = resolve_path("dataset_benchmark/robustness_v2").resolve()
    for name, configured_path in config["outputs"].items():
        output = resolve_path(configured_path).resolve()
        if output != v2_root and v2_root not in output.parents:
            raise ValueError(f"Output {name} escapes robustness_v2: {output}")
    return {"inputs": required_paths, "prompt_checks": prompt_checks}


def record_stage_metadata(
    config: Mapping[str, Any],
    stage: str,
    *,
    inputs: Mapping[str, Path],
    outputs: Mapping[str, Path] | None = None,
    details: Mapping[str, Any] | None = None,
) -> None:
    payload = build_stage_metadata(
        stage,
        inputs=inputs,
        outputs=outputs,
        details={
            "config_hash": canonical_hash(config),
            **dict(details or {}),
        },
    )
    atomic_write_json(checkpoint_path(config, stage), payload)


def stage_validate(config: dict, config_path: Path, args: argparse.Namespace) -> None:
    validation = validate_config(config, config_path)
    record_stage_metadata(
        config,
        "validate_config",
        inputs=validation["inputs"],
        details={"prompt_checks": validation["prompt_checks"]},
    )


def stage_build_manifest(config: dict, config_path: Path, args: argparse.Namespace) -> None:
    rows = selected_variants(config, args)
    output = resolve_path(config["outputs"]["run_manifest"])
    write_jsonl(output, rows)
    record_stage_metadata(
        config,
        "build_manifest",
        inputs={
            "config": config_path,
            "variant_manifest": resolve_path(config["dataset"]["variant_manifest"]),
            "base_manifest": resolve_path(config["dataset"]["base_manifest"]),
        },
        outputs={"run_manifest": output},
        details={"variants": len(rows), "base_ids": len({row["base_id"] for row in rows})},
    )


def stage_generate_augmentation(
    config: dict, config_path: Path, args: argparse.Namespace
) -> None:
    rows = selected_variants(config, args)
    missing = [
        row["variant_id"]
        for row in rows
        if not variant_audio_path(config, row).exists()
    ]
    if missing:
        raise FileNotFoundError(
            f"Selected variants are not generated ({len(missing)} missing); "
            "run Priority 2 generation first"
        )
    record_stage_metadata(
        config,
        "generate_augmentation",
        inputs={
            "config": config_path,
            "variant_manifest": resolve_path(config["dataset"]["variant_manifest"]),
            "augmentation_config": resolve_path(config["dataset"]["augmentation_config"]),
        },
        details={"validated_variants": len(rows), "generated_now": 0},
    )


def stage_stt(config: dict, config_path: Path, args: argparse.Namespace) -> None:
    rows = selected_variants(config, args)
    output = cache_path(config, "stt")
    existing = {
        row["cache_id"]: row for row in read_jsonl(output)
    } if args.resume and output.exists() else {}
    import_path = resolve_path(config["stt"]["compatible_import_cache"])
    imported = {int(row["audio_id"]): row for row in read_jsonl(import_path)}
    cache = dict(existing)
    api_calls = 0
    for row in rows:
        cache_id = row["variant_id"]
        audio_path = variant_audio_path(config, row)
        audio_hash = sha256_file(audio_path)
        key = stt_cache_key(audio_hash, config["stt"])
        if existing.get(cache_id, {}).get("cache_key") == key and existing[cache_id].get("status") == "success":
            continue
        compatible = imported.get(int(row["base_id"])) if row["condition_level"] == "C0" else None
        if compatible and compatible.get("audio_sha256") == audio_hash and compatible.get("status") == "success":
            transcript = compatible.get("raw_transcript", "")
            status = "success"
            origin = "v1_verified_audio_hash"
            latency_ms = 0
            error = None
        else:
            require_paid_api_confirmation(config)
            from app.services.stt_service import speech_to_text

            started = perf_counter()
            transcript = speech_to_text(audio_path.read_bytes(), audio_path.name)
            latency_ms = int((perf_counter() - started) * 1000)
            status = "success" if transcript else "failed"
            origin = "api"
            error = None if transcript else "empty_transcript"
            api_calls += 1
        cache[cache_id] = {
            "cache_id": cache_id,
            "variant_id": row["variant_id"],
            "base_id": row["base_id"],
            "split": row["split"],
            "condition_level": row["condition_level"],
            "audio_sha256": audio_hash,
            "cache_key": key,
            "raw_transcript": transcript,
            "status": status,
            "error": error,
            "latency_ms": latency_ms,
            "cache_origin": origin,
            "model_metadata": dict(config["stt"]),
        }
        write_jsonl(output, cache.values())
    write_jsonl(output, cache.values())
    record_stage_metadata(
        config,
        "stt",
        inputs={
            "config": config_path,
            "run_manifest": resolve_path(config["outputs"]["run_manifest"]),
            **({"compatible_import_cache": import_path} if import_path.exists() else {}),
        },
        outputs={"stt_cache": output},
        details={"records": len(cache), "api_calls": api_calls},
    )


def stage_risk(config: dict, config_path: Path, args: argparse.Namespace) -> None:
    from app.rag.rag_service import retrieve_ranked

    stt_path = cache_path(config, "stt")
    stt_rows = read_jsonl(stt_path)
    selected = {row["variant_id"] for row in selected_variants(config, args)}
    output = cache_path(config, "risk_decisions")
    existing = {
        row["cache_id"]: row for row in read_jsonl(output)
    } if args.resume and output.exists() else {}
    cache = dict(existing)
    detector = HeuristicCorrectionRiskDetector(config["risk_detector"])
    for stt in stt_rows:
        if stt["variant_id"] not in selected:
            continue
        raw = stt.get("raw_transcript", "")
        key = risk_cache_key(raw, config["risk_detector"], config["retrieval"])
        if existing.get(stt["cache_id"], {}).get("cache_key") == key:
            continue
        started = perf_counter()
        retrieval = clean_retrieval(
            retrieve_ranked(
                raw,
                top_k=int(config["retrieval"]["top_k"]),
                use_rerank=bool(config["retrieval"]["use_rerank"]),
            ),
            signal_only=True,
        )
        result = detector.score(
            RiskDetectorInput(
                raw_transcript=raw,
                stt_metadata=stt,
                retrieval_metadata=retrieval,
                audio_metadata={"condition_level": stt["condition_level"]},
            )
        )
        cache[stt["cache_id"]] = {
            "cache_id": stt["cache_id"],
            "variant_id": stt["variant_id"],
            "base_id": stt["base_id"],
            "split": stt["split"],
            "cache_key": key,
            "raw_transcript_sha256": sha256_text(raw),
            **result.to_dict(),
            "retrieval_signal": retrieval,
            "latency_ms": int((perf_counter() - started) * 1000),
            "detector_config_hash": canonical_hash(config["risk_detector"]),
            "retrieval_config_hash": canonical_hash(config["retrieval"]),
        }
    write_jsonl(output, cache.values())
    signature, index_files = index_signature(config)
    record_stage_metadata(
        config,
        "risk_detection",
        inputs={
            "config": config_path,
            "stt_cache": stt_path,
            **{f"index_{path.name}": path for path in index_files},
        },
        outputs={"risk_cache": output},
        details={"records": len(cache), "index_signature": signature},
    )


def stage_correction(config: dict, config_path: Path, args: argparse.Namespace) -> None:
    stt_path = cache_path(config, "stt")
    risk_path = cache_path(config, "risk_decisions")
    stt_rows = {row["cache_id"]: row for row in read_jsonl(stt_path)}
    risk_rows = {row["cache_id"]: row for row in read_jsonl(risk_path)}
    selected = {row["variant_id"] for row in selected_variants(config, args)}
    pipelines = selected_pipelines(config, args)
    output = cache_path(config, "corrections")
    existing = {
        row["cache_id"]: row for row in read_jsonl(output)
    } if args.resume and output.exists() else {}
    import_path = resolve_path(config["correction"]["compatible_import_cache"])
    imported = {int(row["audio_id"]): row for row in read_jsonl(import_path)}
    cache = dict(existing)
    api_calls = 0
    for cache_id, stt in stt_rows.items():
        if stt["variant_id"] not in selected:
            continue
        raw = stt.get("raw_transcript", "")
        risk = risk_rows.get(cache_id, {"decision": "use_raw"})
        required_by = correction_requirements(pipelines, risk["decision"])
        key = correction_cache_key(raw, config["correction"])
        if (
            existing.get(cache_id, {}).get("cache_key") == key
            and existing[cache_id].get("required_by") == list(required_by)
            and existing[cache_id].get("status") in {"success", "skipped", "imported", "not_requested"}
        ):
            continue
        if not required_by:
            cache[cache_id] = {
                "cache_id": cache_id,
                "variant_id": stt["variant_id"],
                "base_id": stt["base_id"],
                "cache_key": key,
                "raw_transcript": raw,
                "corrected_transcript": raw,
                "status": "not_requested",
                "required_by": [],
                "cache_origin": "none",
                "latency_ms": 0,
            }
            write_jsonl(output, cache.values())
            continue
        compatible = imported.get(int(stt["base_id"])) if stt["condition_level"] == "C0" else None
        if (
            compatible
            and compatible.get("raw_transcript") == raw
            and compatible.get("model") == config["correction"]["model"]
            and compatible.get("status") in {"success", "skipped"}
        ):
            corrected = compatible.get("corrected_transcript", raw)
            status = "imported"
            origin = "v1_verified_raw_prompt_model"
            latency_ms = 0
            error = None
            prompt_tokens = compatible.get("prompt_tokens")
            completion_tokens = compatible.get("completion_tokens")
        else:
            require_paid_api_confirmation(config)
            from app.services.asr_correction_service import correct_asr_text

            result = None
            for attempt in range(int(config["correction"]["retry_attempts"])):
                result = correct_asr_text(raw, audio_id=str(stt["base_id"]))
                if result.status in {"success", "skipped"}:
                    break
                if attempt + 1 < int(config["correction"]["retry_attempts"]):
                    sleep(float(config["correction"]["retry_base_delay_seconds"]) * (2**attempt))
            assert result is not None
            corrected = result.corrected_text
            status = result.status
            origin = "api"
            latency_ms = result.latency_ms
            error = result.error
            prompt_tokens = result.prompt_tokens
            completion_tokens = result.completion_tokens
            api_calls += 1
        cache[cache_id] = {
            "cache_id": cache_id,
            "variant_id": stt["variant_id"],
            "base_id": stt["base_id"],
            "cache_key": key,
            "raw_transcript": raw,
            "corrected_transcript": corrected,
            "status": status,
            "required_by": list(required_by),
            "cache_origin": origin,
            "latency_ms": latency_ms,
            "model": config["correction"]["model"],
            "prompt_sha256": config["correction"]["prompt_sha256"],
            "temperature": config["correction"]["temperature"],
            "service_version": config["correction"]["service_version"],
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "error": error,
        }
        write_jsonl(output, cache.values())
    write_jsonl(output, cache.values())
    record_stage_metadata(
        config,
        "correction",
        inputs={
            "config": config_path,
            "stt_cache": stt_path,
            "risk_cache": risk_path,
            "prompt": resolve_path(config["correction"]["prompt_path"]),
            **({"compatible_import_cache": import_path} if import_path.exists() else {}),
        },
        outputs={"correction_cache": output},
        details={"records": len(cache), "api_calls": api_calls, "pipelines": pipelines},
    )


def stage_retrieval(config: dict, config_path: Path, args: argparse.Namespace) -> None:
    from app.rag.rag_service import retrieve_ranked

    stt_path = cache_path(config, "stt")
    risk_path = cache_path(config, "risk_decisions")
    correction_path = cache_path(config, "corrections")
    stt_rows = {row["cache_id"]: row for row in read_jsonl(stt_path)}
    risk_rows = {row["cache_id"]: row for row in read_jsonl(risk_path)}
    corrections = {row["cache_id"]: row for row in read_jsonl(correction_path)}
    selected = {row["variant_id"] for row in selected_variants(config, args)}
    pipelines = selected_pipelines(config, args)
    output = cache_path(config, "retrieval")
    existing = {
        row["cache_id"]: row for row in read_jsonl(output)
    } if args.resume and output.exists() else {}
    cache = dict(existing)
    signature, index_files = index_signature(config)
    for variant_id, stt in stt_rows.items():
        if stt["variant_id"] not in selected:
            continue
        for pipeline in pipelines:
            query, source = select_pipeline_transcript(
                pipeline,
                raw_transcript=stt.get("raw_transcript", ""),
                correction_record=corrections.get(variant_id),
                risk_record=risk_rows.get(variant_id),
            )
            cache_id = f"{variant_id}|{pipeline}"
            key = retrieval_cache_key(query, config["retrieval"], signature)
            if existing.get(cache_id, {}).get("cache_key") == key:
                continue
            started = perf_counter()
            result = clean_retrieval(
                retrieve_ranked(
                    query,
                    top_k=int(config["retrieval"]["top_k"]),
                    use_rerank=bool(config["retrieval"]["use_rerank"]),
                )
            )
            cache[cache_id] = {
                "cache_id": cache_id,
                "variant_id": variant_id,
                "base_id": stt["base_id"],
                "pipeline": pipeline,
                "cache_key": key,
                "query": query,
                "query_source": source,
                "retrieval": result,
                "latency_ms": int((perf_counter() - started) * 1000),
                "index_signature": signature,
                "retrieval_config_hash": canonical_hash(config["retrieval"]),
            }
    write_jsonl(output, cache.values())
    record_stage_metadata(
        config,
        "retrieval",
        inputs={
            "config": config_path,
            "stt_cache": stt_path,
            "risk_cache": risk_path,
            "correction_cache": correction_path,
            **{f"index_{path.name}": path for path in index_files},
        },
        outputs={"retrieval_cache": output},
        details={"records": len(cache), "pipelines": pipelines, "index_signature": signature},
    )


def answer_prompt(question: str, pages: list[dict]) -> str:
    from app.prompts.exam_support import SYSTEM_PROMPT

    context = "\n\n".join(
        f"--- Source: {item['source']} (Page {item['page']}) ---\n{item.get('content', '')}"
        for item in pages
    )
    return f"""{SYSTEM_PROMPT}

[DỮ LIỆU ĐẦU VÀO]
- Câu hỏi của Giám thị: {question}

[TÀI LIỆU HƯỚNG DẪN LIÊN QUAN]
{context}

[YÊU CẦU TRÍCH DẪN]
Chỉ trả lời dựa trên tài liệu và trích dẫn [SOURCE: tên_file_pdf, PAGE: số_trang].
"""


def stage_final_answers(config: dict, config_path: Path, args: argparse.Namespace) -> None:
    retrieval_path = cache_path(config, "retrieval")
    retrieval_rows = read_jsonl(retrieval_path)
    selected = {row["variant_id"] for row in selected_variants(config, args)}
    pipelines = set(selected_pipelines(config, args))
    output = cache_path(config, "final_answers")
    existing = {
        row["cache_id"]: row for row in read_jsonl(output)
    } if args.resume and output.exists() else {}
    cache = dict(existing)
    import_path = resolve_path(config["answer_generation"]["compatible_import_cache"])
    import_retrieval_path = resolve_path(
        config["answer_generation"]["compatible_retrieval_cache"]
    )
    imported_answers = {
        int(row["audio_id"]): row for row in read_jsonl(import_path)
    }
    imported_retrieval = {
        int(row["audio_id"]): row for row in read_jsonl(import_retrieval_path)
    }
    api_calls = 0
    imported_calls = 0
    blocked_calls = 0
    for retrieval in retrieval_rows:
        if retrieval["variant_id"] not in selected or retrieval["pipeline"] not in pipelines:
            continue
        stable_retrieval = {
            "query": retrieval["query"],
            "query_source": retrieval["query_source"],
            "retrieval": retrieval["retrieval"],
            "index_signature": retrieval["index_signature"],
        }
        key = answer_cache_key(canonical_hash(stable_retrieval), config["answer_generation"])
        cache_id = retrieval["cache_id"]
        if existing.get(cache_id, {}).get("cache_key") == key and existing[cache_id].get("status") in {"success", "imported"}:
            continue
        prompt = answer_prompt(
            retrieval["query"], retrieval["retrieval"].get("final_pages", [])
        )
        branch = "proposed" if retrieval["query_source"] == "corrected" else "baseline"
        old_retrieval = imported_retrieval.get(int(retrieval["base_id"]), {})
        old_answer = imported_answers.get(int(retrieval["base_id"]), {}).get(branch, {})
        compatible = (
            old_retrieval.get("queries", {}).get(branch) == retrieval["query"]
            and old_retrieval.get("retrieval", {}).get(branch, {}).get("final_pages")
            == retrieval["retrieval"].get("final_pages")
            and old_answer.get("prompt_sha256") == sha256_text(prompt)
            and old_answer.get("model") == config["answer_generation"]["model"]
        )
        result = None
        error = None
        if compatible:
            answer = old_answer.get("answer", "")
            status = "imported"
            origin = "v1_verified_query_retrieval_prompt"
            latency_ms = 0
            prompt_tokens = old_answer.get("prompt_tokens")
            completion_tokens = old_answer.get("completion_tokens")
            imported_calls += 1
        elif not config["answer_generation"].get("external_api_allowed", False):
            answer = ""
            status = "blocked_external_data_policy"
            origin = "none"
            latency_ms = 0
            prompt_tokens = None
            completion_tokens = None
            error = config["answer_generation"].get("external_api_policy")
            blocked_calls += 1
        else:
            require_paid_api_confirmation(config)
            from app.services.llm_service import generate_answer_with_metadata

            for attempt in range(int(config["answer_generation"]["retry_attempts"])):
                try:
                    result = generate_answer_with_metadata(prompt)
                    break
                except Exception as exc:
                    error = str(exc)
                    if attempt + 1 < int(config["answer_generation"]["retry_attempts"]):
                        sleep(float(config["answer_generation"]["retry_base_delay_seconds"]) * (2**attempt))
            api_calls += 1
            answer = result.text if result else ""
            status = "success" if result else "failed"
            origin = "api"
            latency_ms = result.latency_ms if result else 0
            prompt_tokens = result.prompt_tokens if result else None
            completion_tokens = result.completion_tokens if result else None
        cache[cache_id] = {
            "cache_id": cache_id,
            "variant_id": retrieval["variant_id"],
            "base_id": retrieval["base_id"],
            "pipeline": retrieval["pipeline"],
            "cache_key": key,
            "answer": answer,
            "status": status,
            "cache_origin": origin,
            "error": error,
            "latency_ms": latency_ms,
            "model": config["answer_generation"]["model"],
            "prompt_sha256": config["answer_generation"]["prompt_sha256"],
            "request_prompt_sha256": sha256_text(prompt),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
        }
        write_jsonl(output, cache.values())
    if not output.exists():
        write_jsonl(output, cache.values())
    record_stage_metadata(
        config,
        "final_answers",
        inputs={
            "config": config_path,
            "retrieval_cache": retrieval_path,
            "prompt": resolve_path(config["answer_generation"]["prompt_path"]),
            **({"compatible_import_cache": import_path} if import_path.exists() else {}),
            **(
                {"compatible_retrieval_cache": import_retrieval_path}
                if import_retrieval_path.exists()
                else {}
            ),
        },
        outputs={"answer_cache": output},
        details={
            "records": len(cache),
            "api_calls": api_calls,
            "imported_calls": imported_calls,
            "blocked_calls": blocked_calls,
            "pipelines": sorted(pipelines),
            "external_api_allowed": config["answer_generation"].get(
                "external_api_allowed", False
            ),
        },
    )


def stage_judge(config: dict, config_path: Path, args: argparse.Namespace) -> None:
    """Run the optional cached auxiliary judge; human ratings remain primary."""

    final_path = cache_path(config, "final_answers")
    if not config.get("judge", {}).get("enabled", False):
        record_stage_metadata(
            config,
            "judge",
            inputs={"config": config_path, "final_answer_cache": final_path},
            details={
                "enabled": False,
                "availability": "unavailable_disabled_by_config",
                "role": "auxiliary_only_human_rating_is_primary",
                "api_calls": 0,
            },
        )
        return

    from dotenv import load_dotenv
    from openai import OpenAI

    load_dotenv()
    selected = {row["variant_id"] for row in selected_variants(config, args)}
    pipelines = set(selected_pipelines(config, args))
    manifest_rows = {
        row["variant_id"]: row
        for row in read_jsonl(resolve_path(config["outputs"]["run_manifest"]))
    }
    retrieval_path = cache_path(config, "retrieval")
    retrieval_rows = {row["cache_id"]: row for row in read_jsonl(retrieval_path)}
    final_rows = read_jsonl(final_path)
    output = cache_path(config, "judge")
    existing = {
        row["cache_id"]: row for row in read_jsonl(output)
    } if args.resume and output.exists() else {}
    cache = dict(existing)
    prompt_path = resolve_path(config["judge"]["prompt_path"])
    system_prompt = prompt_path.read_text(encoding="utf-8")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    api_calls = 0
    excluded = 0
    for answer in final_rows:
        if answer["variant_id"] not in selected or answer["pipeline"] not in pipelines:
            continue
        retrieval = retrieval_rows.get(answer["cache_id"], {})
        manifest = manifest_rows.get(answer["variant_id"], {})
        key = canonical_hash(
            {
                "answer_cache_key": answer.get("cache_key"),
                "retrieval_cache_key": retrieval.get("cache_key"),
                "reference_sha256": sha256_text(manifest.get("reference_transcript", "")),
                "judge_config": config["judge"],
            }
        )
        cache_id = answer["cache_id"]
        if existing.get(cache_id, {}).get("cache_key") == key and existing[cache_id].get("status") == "success":
            continue
        if answer.get("status") not in {"success", "imported"} or not answer.get("answer"):
            cache[cache_id] = {
                "cache_id": cache_id,
                "variant_id": answer["variant_id"],
                "base_id": answer["base_id"],
                "pipeline": answer["pipeline"],
                "cache_key": key,
                "status": "excluded_missing_answer",
                "error": answer.get("error") or answer.get("status"),
                "cache_origin": "none",
            }
            excluded += 1
            continue
        pages = retrieval.get("retrieval", {}).get("final_pages", [])
        evidence = "\n\n".join(
            f"[{page.get('source')} p.{page.get('page')}] {str(page.get('content', ''))[:4000]}"
            for page in pages
        )
        user_prompt = (
            f"Ý định/reference transcript:\n{manifest.get('reference_transcript', '')}\n\n"
            f"Câu trả lời cần chấm:\n{answer['answer']}\n\n"
            f"Bằng chứng truy xuất:\n{evidence or '[không có]'}"
        )
        result = None
        error = None
        started = perf_counter()
        for attempt in range(int(config["judge"]["retry_attempts"])):
            try:
                require_paid_api_confirmation(config)
                result = client.chat.completions.create(
                    model=config["judge"]["model"],
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=float(config["judge"]["temperature"]),
                    response_format={"type": "json_object"},
                )
                break
            except Exception as exc:
                error = str(exc)
                if attempt + 1 < int(config["judge"]["retry_attempts"]):
                    sleep(float(config["judge"]["retry_base_delay_seconds"]) * (2**attempt))
        api_calls += 1
        usage = getattr(result, "usage", None) if result else None
        raw_score = result.choices[0].message.content.strip() if result else ""
        try:
            scores = json.loads(raw_score) if raw_score else None
        except json.JSONDecodeError:
            scores = None
            error = "judge_returned_invalid_json"
        cache[cache_id] = {
            "cache_id": cache_id,
            "variant_id": answer["variant_id"],
            "base_id": answer["base_id"],
            "pipeline": answer["pipeline"],
            "cache_key": key,
            "status": "success" if scores is not None else "failed",
            "scores": scores,
            "raw_response": raw_score,
            "error": error,
            "cache_origin": "api",
            "latency_ms": int((perf_counter() - started) * 1000),
            "model": config["judge"]["model"],
            "prompt_sha256": config["judge"]["prompt_sha256"],
            "request_prompt_sha256": sha256_text(user_prompt),
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "role": "auxiliary_only_human_rating_is_primary",
        }
        write_jsonl(output, cache.values())
    if not output.exists():
        write_jsonl(output, cache.values())
    record_stage_metadata(
        config,
        "judge",
        inputs={
            "config": config_path,
            "run_manifest": resolve_path(config["outputs"]["run_manifest"]),
            "final_answer_cache": final_path,
            "retrieval_cache": retrieval_path,
            "judge_prompt": prompt_path,
        },
        outputs={"judge_cache": output},
        details={
            "enabled": True,
            "records": len(cache),
            "api_calls": api_calls,
            "excluded": excluded,
            "role": "auxiliary_only_human_rating_is_primary",
        },
    )


def stage_evaluate(config: dict, config_path: Path, args: argparse.Namespace) -> None:
    summary = evaluate(config, config_path)
    outputs = config["outputs"]
    record_stage_metadata(
        config,
        "evaluate",
        inputs={
            "config": config_path,
            "run_manifest": resolve_path(outputs["run_manifest"]),
            "stt_cache": cache_path(config, "stt"),
            "risk_cache": cache_path(config, "risk_decisions"),
            "correction_cache": cache_path(config, "corrections"),
            "retrieval_cache": cache_path(config, "retrieval"),
            "final_answer_cache": cache_path(config, "final_answers"),
            **(
                {"judge_cache": cache_path(config, "judge")}
                if cache_path(config, "judge").exists()
                else {}
            ),
            "gold_manifest": resolve_path(config["evaluation"]["gold_manifest"]),
        },
        outputs={
            "evaluation_summary": resolve_path(outputs["evaluation_summary"]),
            "metrics_csv": resolve_path(outputs["metrics_csv"]),
            "sample_level_csv": resolve_path(outputs["sample_level_csv"]),
            "base_level_csv": resolve_path(outputs["base_level_csv"]),
        },
        details={
            "independent_base_utterances": summary["dataset"]["independent_base_utterances"],
            "pipeline_records": summary["dataset"]["pipeline_records"],
            "resampling_unit": summary["statistics"]["resampling_unit"],
        },
    )


def stage_report(config: dict, config_path: Path, args: argparse.Namespace) -> None:
    outputs = config["outputs"]
    summary_path = resolve_path(outputs["evaluation_summary"])
    report_path = resolve_path(outputs["report_markdown"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = report_path.with_suffix(report_path.suffix + ".tmp")
    temporary.write_text(generate(config), encoding="utf-8", newline="\n")
    os.replace(temporary, report_path)
    record_stage_metadata(
        config,
        "report",
        inputs={"config": config_path, "evaluation_summary": summary_path},
        outputs={"report_markdown": report_path},
        details={"production_modified": False},
    )


def dry_run(config: dict, config_path: Path, args: argparse.Namespace) -> dict:
    validate_config(config, config_path)
    rows = selected_variants(config, args)
    pipelines = selected_pipelines(config, args)
    raw_import = {int(row["audio_id"]): row for row in read_jsonl(resolve_path(config["stt"]["compatible_import_cache"]))}
    corrected_import = {int(row["audio_id"]): row for row in read_jsonl(resolve_path(config["correction"]["compatible_import_cache"]))}
    stt_importable = sum(
        row["condition_level"] == "C0"
        and raw_import.get(int(row["base_id"]), {}).get("audio_sha256") == row["source_audio_sha256"]
        for row in rows
    )
    correction_importable = sum(
        row["condition_level"] == "C0"
        and int(row["base_id"]) in corrected_import
        and int(row["base_id"]) in raw_import
        and corrected_import[int(row["base_id"])].get("raw_transcript")
        == raw_import[int(row["base_id"])].get("raw_transcript")
        for row in rows
    )
    stt_calls = len(rows) - stt_importable
    correction_calls = 0 if "P1" not in pipelines and "P2" not in pipelines else len(rows) - correction_importable
    answer_total = len(rows) * len(pipelines)
    answer_importable = 0
    retrieval_cache = cache_path(config, "retrieval")
    if retrieval_cache.exists():
        selected_ids = {row["variant_id"] for row in rows}
        old_answers = {
            int(row["audio_id"]): row
            for row in read_jsonl(
                resolve_path(config["answer_generation"]["compatible_import_cache"])
            )
        }
        old_retrieval = {
            int(row["audio_id"]): row
            for row in read_jsonl(
                resolve_path(config["answer_generation"]["compatible_retrieval_cache"])
            )
        }
        for retrieval in read_jsonl(retrieval_cache):
            if retrieval["variant_id"] not in selected_ids or retrieval["pipeline"] not in pipelines:
                continue
            branch = "proposed" if retrieval["query_source"] == "corrected" else "baseline"
            previous_retrieval = old_retrieval.get(int(retrieval["base_id"]), {})
            previous_answer = old_answers.get(int(retrieval["base_id"]), {}).get(branch, {})
            prompt = answer_prompt(
                retrieval["query"], retrieval["retrieval"].get("final_pages", [])
            )
            if (
                previous_retrieval.get("queries", {}).get(branch) == retrieval["query"]
                and previous_retrieval.get("retrieval", {}).get(branch, {}).get("final_pages")
                == retrieval["retrieval"].get("final_pages")
                and previous_answer.get("prompt_sha256") == sha256_text(prompt)
                and previous_answer.get("model") == config["answer_generation"]["model"]
            ):
                answer_importable += 1
    answer_unresolved = answer_total - answer_importable
    external_allowed = bool(config["answer_generation"].get("external_api_allowed", False))
    answer_calls = answer_unresolved if external_allowed else 0
    answer_blocked = 0 if external_allowed else answer_unresolved
    judge_enabled = bool(config.get("judge", {}).get("enabled", False))
    judge_existing = 0
    judge_cache = cache_path(config, "judge")
    if judge_enabled and judge_cache.exists():
        selected_cache_ids = {
            f"{row['variant_id']}|{pipeline}" for row in rows for pipeline in pipelines
        }
        judge_existing = sum(
            row.get("cache_id") in selected_cache_ids and row.get("status") == "success"
            for row in read_jsonl(judge_cache)
        )
    judge_calls = max(0, answer_total - judge_existing) if judge_enabled else 0
    prices = config["cost"]["models"]["gpt-4o-mini"]
    estimates = config["cost"]["estimates"]
    correction_cost = correction_calls * (
        estimates["correction_input_tokens_per_call"] * prices["input_per_million_tokens"]
        + estimates["correction_output_tokens_per_call"] * prices["output_per_million_tokens"]
    ) / 1_000_000
    answer_cost = answer_calls * (
        estimates["answer_input_tokens_per_call"] * prices["input_per_million_tokens"]
        + estimates["answer_output_tokens_per_call"] * prices["output_per_million_tokens"]
    ) / 1_000_000
    judge_cost = judge_calls * (
        estimates.get("judge_input_tokens_per_call", 3000) * prices["input_per_million_tokens"]
        + estimates.get("judge_output_tokens_per_call", 120) * prices["output_per_million_tokens"]
    ) / 1_000_000
    duration_seconds = 0.0
    stt_duration_seconds = 0.0
    bytes_total = 0
    for row in rows:
        path = variant_audio_path(config, row)
        bytes_total += path.stat().st_size
        with wave.open(str(path), "rb") as handle:
            duration = handle.getnframes() / handle.getframerate()
            duration_seconds += duration
            compatible = raw_import.get(int(row["base_id"])) if row["condition_level"] == "C0" else None
            if not (
                compatible
                and compatible.get("audio_sha256") == row["source_audio_sha256"]
                and compatible.get("status") == "success"
            ):
                stt_duration_seconds += duration
    stt_cost = stt_duration_seconds / 60 * float(
        config["cost"]["models"]["gpt-4o-mini-transcribe"]["per_minute_assumption"]
    ) if stt_calls else 0.0
    total = stt_cost + correction_cost + answer_cost + judge_cost
    return {
        "mode": config.get("execution", {}).get("mode", "priority3_pilot_dry_run"),
        "base_samples": len({row["base_id"] for row in rows}),
        "audio_variants": len(rows),
        "conditions": sorted({row["condition_level"] for row in rows}),
        "pipelines": list(pipelines),
        "audio_bytes": bytes_total,
        "audio_mib": round(bytes_total / 1024 / 1024, 3),
        "audio_minutes": round(duration_seconds / 60, 3),
        "stt_billable_minutes_estimate": round(stt_duration_seconds / 60, 3),
        "compatible_cache": {
            "stt_rows": stt_importable,
            "correction_rows": correction_importable,
            "final_answer_rows": answer_importable,
            "judge_rows": judge_existing,
        },
        "estimated_api_calls": {
            "stt": stt_calls,
            "correction": correction_calls,
            "final_answers": answer_calls,
            "judge": judge_calls,
            "total": stt_calls + correction_calls + answer_calls + judge_calls,
        },
        "blocked_by_external_data_policy": {
            "final_answers": answer_blocked,
            "policy": config["answer_generation"].get("external_api_policy"),
        },
        "estimated_cost_usd": {
            "stt": round(stt_cost, 6),
            "correction": round(correction_cost, 6),
            "final_answers": round(answer_cost, 6),
            "judge": round(judge_cost, 6),
            "total": round(total, 6),
        },
        "paid_api_confirmation": {
            "required": bool(config.get("execution", {}).get("requires_paid_api_confirmation", False)),
            "env_var": config.get("execution", {}).get("confirmation_env_var"),
            "review_before_execution": True,
        },
        "cost_approval_required": total > float(config["cost"]["approval_threshold_usd"]),
        "writes_performed": False,
        "config_hash": canonical_hash(config),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="dataset_benchmark/robustness_v2/configs/benchmark_v2_config.json")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--stage", action="append", choices=PRIORITY3_STAGES + PRIORITY4_STAGES)
    parser.add_argument("--force-stage", action="append", choices=PRIORITY3_STAGES)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--base-id", action="append", type=int)
    parser.add_argument("--condition", choices=("C0", "C1", "C2", "C3"))
    parser.add_argument("--pipeline", action="append", choices=PIPELINES)
    parser.add_argument("--validate-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")
    args = parse_args()
    config_path = resolve_path(args.config)
    config = load_config(config_path)
    if args.dry_run:
        print(json.dumps(dry_run(config, config_path, args), ensure_ascii=False, indent=2))
        return
    if args.validate_only:
        stage_validate(config, config_path, args)
        print("Configuration and prompt locks are valid.")
        return
    stages = args.stage or list(PRIORITY3_STAGES + PRIORITY4_STAGES)
    handlers: dict[str, Callable[[dict, Path, argparse.Namespace], None]] = {
        "validate_config": stage_validate,
        "build_manifest": stage_build_manifest,
        "generate_augmentation": stage_generate_augmentation,
        "stt": stage_stt,
        "risk_detection": stage_risk,
        "correction": stage_correction,
        "retrieval": stage_retrieval,
        "final_answers": stage_final_answers,
        "judge": stage_judge,
        "evaluate": stage_evaluate,
        "report": stage_report,
    }
    for stage in stages:
        if stage in set(args.force_stage or []):
            output_names = {
                "stt": "stt",
                "risk_detection": "risk_decisions",
                "correction": "corrections",
                "retrieval": "retrieval",
                "final_answers": "final_answers",
            }
            if stage in output_names:
                cache_path(config, output_names[stage]).unlink(missing_ok=True)
        print(f"== {stage} ==")
        handlers[stage](config, config_path, args)
    run_record = {
        "schema_version": "1.0.0",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "stages": stages,
        "base_limit": args.limit or config["dataset"]["pilot_max_base"],
        "base_ids": sorted({int(row["base_id"]) for row in selected_variants(config, args)}),
        "base_selection": "filter condition; ascending (int(base_id), variant_id); first N unique base IDs; no random seed",
        "condition": args.condition or config["dataset"]["default_condition"],
        "pipelines": selected_pipelines(config, args),
        "config_hash": canonical_hash(config),
    }
    complete_stage_order = list(PRIORITY3_STAGES + PRIORITY4_STAGES)
    run_name = (
        config.get("execution", {}).get("full_run_record_name", "priority4_run.json")
        if stages == complete_stage_order
        else "last_partial_run.json"
    )
    atomic_write_json(
        resolve_path(config["outputs"]["checkpoint_dir"]) / run_name,
        run_record,
    )


if __name__ == "__main__":
    main()
