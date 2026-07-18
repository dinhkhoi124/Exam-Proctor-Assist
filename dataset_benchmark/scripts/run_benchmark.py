from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import random
from time import perf_counter, sleep

try:
    from .annotations import create_answer_templates, create_gold_templates
    from .build_manifest import build_manifest
    from .common import (
        atomic_write_json,
        atomic_write_jsonl,
        load_config,
        read_jsonl,
        resolve_path,
        sha256_file,
        sha256_text,
    )
except ImportError:
    from annotations import create_answer_templates, create_gold_templates
    from build_manifest import build_manifest
    from common import (
        atomic_write_json,
        atomic_write_jsonl,
        load_config,
        read_jsonl,
        resolve_path,
        sha256_file,
        sha256_text,
    )


def read_manifest(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def eligible_rows(manifest_path: Path) -> list[dict]:
    return [
        row
        for row in read_manifest(manifest_path)
        if row["eligibility_status"] == "eligible"
    ]


def selected_rows(config: dict) -> list[dict]:
    rows = eligible_rows(resolve_path(config["manifest"]))
    selected_split = config.get("_sample_split", "all")
    if selected_split in {"dev", "test"}:
        rows = [row for row in rows if row["split"] == selected_split]
    limit = config.get("_limit")
    return rows[: int(limit)] if limit is not None else rows


def _save_cache(path: Path, cache: dict[int, dict]) -> None:
    atomic_write_jsonl(path, cache.values())


def stage_manifest(config: dict, resume: bool = False) -> None:
    manifest_path = resolve_path(config["manifest"])
    records = build_manifest(
        resolve_path(config["ground_truth"]),
        resolve_path(config["audio_dir"]),
        manifest_path,
    )
    eligible = [row for row in records if row["eligibility_status"] == "eligible"]
    expected_eligible = int(config.get("dataset", {}).get("eligible_samples", 130))
    if len(eligible) != expected_eligible:
        raise RuntimeError(
            "Manifest invariant failed: "
            f"expected {expected_eligible} eligible, got {len(eligible)}"
        )
    create_gold_templates(
        manifest_path,
        resolve_path(config["annotation_dir"]),
        overwrite=not resume,
    )


def stage_transcribe(config: dict, resume: bool) -> None:
    from app.services.stt_service import STT_PROMPT, speech_to_text

    output = resolve_path(config["output_dir"]) / "raw_transcripts.jsonl"
    cache = {int(row["audio_id"]): row for row in read_jsonl(output)} if resume else {}
    attempts = int(config.get("retry_attempts", 3))
    base_delay = float(config.get("retry_base_delay_seconds", 1.0))

    for manifest in selected_rows(config):
        audio_id = int(manifest["audio_id"])
        audio_path = resolve_path(manifest["audio_path"])
        audio_hash = sha256_file(audio_path)
        input_hash = sha256_text(
            "|".join(
                [audio_hash, "gpt-4o-mini-transcribe", "whisper-1", STT_PROMPT]
            )
        )
        cached = cache.get(audio_id, {})
        if (
            cached.get("input_sha256") == input_hash
            and cached.get("status") == "success"
        ):
            continue

        transcript = ""
        error = None
        started = perf_counter()
        for attempt in range(attempts):
            transcript = speech_to_text(audio_path.read_bytes(), audio_path.name)
            if transcript:
                break
            error = "empty_transcript"
            if attempt + 1 < attempts:
                sleep(base_delay * (2**attempt))
        cache[audio_id] = {
            "audio_id": audio_id,
            "audio_sha256": audio_hash,
            "input_sha256": input_hash,
            "raw_transcript": transcript,
            "status": "success" if transcript else "failed",
            "error": error,
            "latency_ms": int((perf_counter() - started) * 1000),
            "primary_model": "gpt-4o-mini-transcribe",
            "fallback_model": "whisper-1",
        }
        _save_cache(output, cache)


def stage_correction(config: dict, resume: bool) -> None:
    from app.services.asr_correction_service import correct_asr_text
    from app.core.config import ASR_CORRECTION_MODEL
    from app.prompts.asr_correction import ASR_CORRECTION_SYSTEM_PROMPT

    output_dir = resolve_path(config["output_dir"])
    raw_rows = {int(row["audio_id"]): row for row in read_jsonl(output_dir / "raw_transcripts.jsonl")}
    output = output_dir / "corrected_transcripts.jsonl"
    cache = {int(row["audio_id"]): row for row in read_jsonl(output)} if resume else {}
    attempts = int(config.get("retry_attempts", 3))
    base_delay = float(config.get("retry_base_delay_seconds", 1.0))

    for manifest in selected_rows(config):
        audio_id = int(manifest["audio_id"])
        raw = raw_rows.get(audio_id, {}).get("raw_transcript", "")
        input_hash = sha256_text(
            "|".join([raw, ASR_CORRECTION_MODEL, ASR_CORRECTION_SYSTEM_PROMPT])
        )
        cached = cache.get(audio_id, {})
        if (
            cached.get("input_sha256") == input_hash
            and cached.get("status") in {"success", "skipped"}
        ):
            continue
        result = None
        for attempt in range(attempts):
            result = correct_asr_text(raw, audio_id=str(audio_id))
            if result.status in {"success", "skipped"}:
                break
            if attempt + 1 < attempts:
                sleep(base_delay * (2**attempt))
        assert result is not None
        cache[audio_id] = {
            "audio_id": audio_id,
            "input_sha256": input_hash,
            "raw_transcript": raw,
            "corrected_transcript": result.corrected_text,
            "status": result.status,
            "latency_ms": result.latency_ms,
            "model": result.model,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "error": result.error,
        }
        _save_cache(output, cache)


def _clean_retrieval(result: dict) -> dict:
    def clean_item(item: dict) -> dict:
        return {
            key: value
            for key, value in item.items()
            if key not in {"image_base64", "base64"}
        }

    return {
        "status": result["status"],
        "candidates": [clean_item(item) for item in result["candidates"]],
        "final_pages": [clean_item(item) for item in result["final_pages"]],
    }


def stage_retrieval(config: dict, resume: bool) -> None:
    from app.rag.rag_service import retrieve_ranked

    output_dir = resolve_path(config["output_dir"])
    raw_rows = {int(row["audio_id"]): row for row in read_jsonl(output_dir / "raw_transcripts.jsonl")}
    corrected_rows = {int(row["audio_id"]): row for row in read_jsonl(output_dir / "corrected_transcripts.jsonl")}
    output = output_dir / "retrieval_results.jsonl"
    cache = {int(row["audio_id"]): row for row in read_jsonl(output)} if resume else {}
    top_k = int(config.get("top_k", 15))
    use_rerank = bool(config.get("use_rerank", False))
    vector_dir = resolve_path("backend/app/rag/vector_store")
    index_files = [
        vector_dir / name
        for name in ("index.faiss", "metadata.json", "bm25.pkl", "bm25_corpus.json")
        if (vector_dir / name).exists()
    ]
    index_signature = sha256_text(
        "|".join(f"{path.name}:{sha256_file(path)}" for path in index_files)
    )

    for manifest in selected_rows(config):
        audio_id = int(manifest["audio_id"])
        queries = {
            "baseline": raw_rows.get(audio_id, {}).get("raw_transcript", ""),
            "proposed": corrected_rows.get(audio_id, {}).get("corrected_transcript", ""),
            "reference": manifest["reference_transcript"],
        }
        input_hash = sha256_text(
            str(top_k) + str(use_rerank) + index_signature + repr(queries)
        )
        if cache.get(audio_id, {}).get("input_sha256") == input_hash:
            continue
        started = perf_counter()
        retrieval = {
            branch: _clean_retrieval(
                retrieve_ranked(query, top_k=top_k, use_rerank=use_rerank)
            )
            for branch, query in queries.items()
        }
        cache[audio_id] = {
            "audio_id": audio_id,
            "input_sha256": input_hash,
            "queries": queries,
            "retrieval": retrieval,
            "latency_ms": int((perf_counter() - started) * 1000),
            "top_k": top_k,
            "use_rerank": use_rerank,
            "index_signature": index_signature,
        }
        _save_cache(output, cache)


def _answer_prompt(question: str, pages: list[dict]) -> str:
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


def stage_answers(config: dict, resume: bool) -> None:
    from app.services.llm_service import generate_answer_with_metadata

    output_dir = resolve_path(config["output_dir"])
    retrieval_rows = {int(row["audio_id"]): row for row in read_jsonl(output_dir / "retrieval_results.jsonl")}
    output = output_dir / "answer_results.jsonl"
    cache = {int(row["audio_id"]): row for row in read_jsonl(output)} if resume else {}

    answer_split = config.get("_sample_split", "all")
    for manifest in selected_rows(config):
        if answer_split == "all" and manifest["split"] != "test":
            continue
        audio_id = int(manifest["audio_id"])
        retrieval_row = retrieval_rows.get(audio_id)
        if not retrieval_row:
            continue
        input_hash = sha256_text(retrieval_row["input_sha256"] + "|answers-v1")
        cached = cache.get(audio_id, {})
        if (
            cached.get("input_sha256") == input_hash
            and cached.get("status") == "success"
        ):
            continue
        branches = {}
        for branch in ("baseline", "proposed"):
            query = retrieval_row["queries"][branch]
            pages = retrieval_row["retrieval"][branch]["final_pages"]
            prompt = _answer_prompt(query, pages)
            result = generate_answer_with_metadata(prompt)
            branches[branch] = {
                "answer": result.text,
                "latency_ms": result.latency_ms,
                "model": result.model,
                "prompt_tokens": result.prompt_tokens,
                "completion_tokens": result.completion_tokens,
                "retrieved_pages": [
                    {"source": page.get("source"), "page": page.get("page")}
                    for page in pages
                ],
                "prompt_sha256": sha256_text(prompt),
            }
        cache[audio_id] = {
            "audio_id": audio_id,
            "input_sha256": input_hash,
            **branches,
        }
        _save_cache(output, cache)

    if config.get("_limit") is None and config.get("_sample_split", "all") in {
        "all",
        "test",
    }:
        create_answer_templates(
            resolve_path(config["manifest"]),
            output,
            output_dir / "retrieval_results.jsonl",
            resolve_path(config["annotation_dir"]),
            seed=int(config.get("human_subset_seed", 43)),
            overwrite=not resume,
        )


def stage_judge(config: dict, resume: bool) -> None:
    """Secondary LLM-as-judge signal; human grading remains primary."""
    from app.services.llm_service import client

    output_dir = resolve_path(config["output_dir"])
    answers = {
        int(row["audio_id"]): row
        for row in read_jsonl(output_dir / "answer_results.jsonl")
    }
    retrieval = {
        int(row["audio_id"]): row
        for row in read_jsonl(output_dir / "retrieval_results.jsonl")
    }
    manifest = {
        int(row["audio_id"]): row
        for row in selected_rows(config)
        if config.get("_sample_split", "all") != "all" or row["split"] == "test"
    }
    output = output_dir / "judge_results.jsonl"
    cache = {int(row["audio_id"]): row for row in read_jsonl(output)} if resume else {}
    attempts = int(config.get("retry_attempts", 3))

    for audio_id in sorted(set(manifest) & set(answers)):
        answer_row = answers[audio_id]
        input_hash = sha256_text(answer_row["input_sha256"] + "|judge-v1")
        cached = cache.get(audio_id, {})
        if (
            cached.get("input_sha256") == input_hash
            and cached.get("status") == "success"
        ):
            continue
        rng = random.Random(int(config.get("human_subset_seed", 43)) + audio_id)
        swapped = bool(rng.getrandbits(1))
        first_branch, second_branch = (
            ("proposed", "baseline") if swapped else ("baseline", "proposed")
        )
        evidence_a = retrieval.get(audio_id, {}).get("retrieval", {}).get(first_branch, {}).get("final_pages", [])
        evidence_b = retrieval.get(audio_id, {}).get("retrieval", {}).get(second_branch, {}).get("final_pages", [])
        prompt = f"""Bạn là giám khảo phụ cho benchmark RAG. Không được đoán pipeline.
Đánh giá độc lập hai câu trả lời theo transcript tham chiếu. Đây chỉ là tín hiệu tự động phụ.

Transcript tham chiếu: {manifest[audio_id]['reference_transcript']}

Evidence A: {json.dumps(evidence_a, ensure_ascii=False)}
Answer A: {answer_row[first_branch]['answer']}

Evidence B: {json.dumps(evidence_b, ensure_ascii=False)}
Answer B: {answer_row[second_branch]['answer']}

Trả JSON object với đúng cấu trúc:
{{"A": {{"correctness": 1, "faithfulness": 1, "completeness": 1, "citation": 1, "task_success": 0}},
  "B": {{"correctness": 1, "faithfulness": 1, "completeness": 1, "citation": 1, "task_success": 0}}}}
Các rubric dùng số nguyên 1-5; task_success dùng 0 hoặc 1.
"""
        parsed = None
        response = None
        error = None
        started = perf_counter()
        for attempt in range(attempts):
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                    response_format={"type": "json_object"},
                )
                parsed = json.loads(response.choices[0].message.content)
                break
            except Exception as exc:
                error = str(exc)
                if attempt + 1 < attempts:
                    sleep(float(config.get("retry_base_delay_seconds", 1.0)) * (2**attempt))
        usage = getattr(response, "usage", None) if response is not None else None
        scores = {}
        if parsed:
            scores[first_branch] = parsed["A"]
            scores[second_branch] = parsed["B"]
        cache[audio_id] = {
            "audio_id": audio_id,
            "input_sha256": input_hash,
            "model": "gpt-4o-mini",
            "status": "success" if parsed else "failed",
            "scores": scores,
            "latency_ms": int((perf_counter() - started) * 1000),
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "error": error,
            "disclosure": "Secondary LLM judge; same model family as generator.",
        }
        _save_cache(output, cache)


def write_run_metadata(config: dict, stages: list[str]) -> None:
    output_dir = resolve_path(config["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    atomic_write_json(
        output_dir / "run_manifest.json",
        {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "stages": stages,
            "config": config,
            "voice_pipeline_mode": os.getenv("VOICE_PIPELINE_MODE", "baseline"),
            "correction_prompt_sha256": sha256_file(
                resolve_path("backend/app/prompts/asr_correction.py")
            ),
            "benchmark_runner_sha256": sha256_file(Path(__file__)),
        },
    )


def validate_prompt_lock(config: dict, sample_split: str) -> None:
    if sample_split != "test":
        return
    prompt_lock = config.get("prompt_lock", {})
    expected = prompt_lock.get("sha256")
    if prompt_lock.get("status") != "locked" or not expected:
        raise RuntimeError("Test run requires a locked correction prompt hash")
    actual = sha256_file(resolve_path("backend/app/prompts/asr_correction.py"))
    if actual != expected:
        raise RuntimeError(
            "Correction prompt changed after lock: "
            f"expected {expected}, got {actual}. Do not run the test split."
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="dataset_benchmark/benchmark_config.json")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument(
        "--sample-split", choices=("all", "dev", "test"), default="all"
    )
    parser.add_argument(
        "--stages",
        default="manifest,transcribe,correction,retrieval,answers,judge,evaluate,report",
        help="Comma-separated stages",
    )
    args = parser.parse_args()
    config = load_config(args.config)
    validate_prompt_lock(config, args.sample_split)
    config["_limit"] = args.limit
    config["_sample_split"] = args.sample_split
    stages = [stage.strip() for stage in args.stages.split(",") if stage.strip()]
    write_run_metadata(config, stages)

    handlers = {
        "manifest": lambda: stage_manifest(config, args.resume),
        "transcribe": lambda: stage_transcribe(config, args.resume),
        "correction": lambda: stage_correction(config, args.resume),
        "retrieval": lambda: stage_retrieval(config, args.resume),
        "answers": lambda: stage_answers(config, args.resume),
        "judge": lambda: stage_judge(config, args.resume),
    }
    for stage in stages:
        if stage in handlers:
            print(f"== {stage} ==")
            handlers[stage]()
        elif stage == "evaluate":
            print("== evaluate ==")
            from evaluate import evaluate
            evaluate(config)
        elif stage == "report":
            print("== report ==")
            from generate_report import generate_report
            generate_report(config)
        else:
            raise ValueError(f"Unknown stage: {stage}")


if __name__ == "__main__":
    main()
