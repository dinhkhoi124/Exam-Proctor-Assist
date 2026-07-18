from __future__ import annotations

import json
from pathlib import Path

try:
    from .common import load_config, resolve_path
except ImportError:
    from common import load_config, resolve_path


def _pct(value) -> str:
    return "N/A" if value is None else f"{100 * float(value):.2f}%"


def _charts(metrics: dict, output_dir: Path) -> list[str]:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        return []
    paths = []
    transcript = metrics.get("transcript", {})
    if transcript:
        fig, axis = plt.subplots(figsize=(6, 4))
        axis.bar(
            ["Baseline", "Proposed"],
            [transcript.get("baseline_wer", 0), transcript.get("proposed_wer", 0)],
            color=["#64748b", "#f97316"],
        )
        axis.set_ylabel("WER")
        axis.set_title("Word Error Rate")
        fig.tight_layout()
        path = output_dir / "wer_comparison.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        paths.append(path.name)
    proxy = metrics.get("retrieval_proxy", {})
    if proxy.get("samples"):
        fig, axis = plt.subplots(figsize=(6, 4))
        axis.bar(
            ["Baseline", "Proposed"],
            [
                proxy.get("baseline", {}).get("jaccard_at_5", 0),
                proxy.get("proposed", {}).get("jaccard_at_5", 0),
            ],
            color=["#64748b", "#f97316"],
        )
        axis.set_ylabel("Proxy Jaccard@5")
        axis.set_title("Retrieval overlap with reference-transcript query")
        fig.tight_layout()
        path = output_dir / "retrieval_proxy.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        paths.append(path.name)
    gold = metrics.get("retrieval_gold", {})
    if gold.get("samples"):
        fig, axis = plt.subplots(figsize=(7, 4))
        labels = ["Hit@1", "Hit@3", "Hit@5", "MRR@10"]
        keys = ["hit_at_1", "hit_at_3", "hit_at_5", "mrr_at_10"]
        x = range(len(labels))
        axis.bar([value - 0.18 for value in x], [gold["baseline"][key] for key in keys], width=0.36, label="Baseline")
        axis.bar([value + 0.18 for value in x], [gold["proposed"][key] for key in keys], width=0.36, label="Proposed")
        axis.set_xticks(list(x), labels)
        axis.legend()
        axis.set_title("Gold retrieval metrics")
        fig.tight_layout()
        path = output_dir / "retrieval_gold.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        paths.append(path.name)
    human = metrics.get("human_answers", {})
    if human.get("graded_records"):
        fig, axis = plt.subplots(figsize=(6, 4))
        axis.bar(
            ["Baseline", "Proposed"],
            [human["baseline"].get("task_success") or 0, human["proposed"].get("task_success") or 0],
            color=["#64748b", "#f97316"],
        )
        axis.set_ylim(0, 1)
        axis.set_title("Human-rated task success")
        fig.tight_layout()
        path = output_dir / "task_success.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        paths.append(path.name)
    correction = metrics.get("system", {}).get("correction", {})
    if correction.get("samples"):
        fig, axis = plt.subplots(figsize=(6, 4))
        axis.bar(["p50", "p95"], [correction.get("p50_latency_ms") or 0, correction.get("p95_latency_ms") or 0], color="#f97316")
        axis.set_ylabel("Milliseconds")
        axis.set_title("ASR correction latency")
        fig.tight_layout()
        path = output_dir / "correction_latency.png"
        fig.savefig(path, dpi=160)
        plt.close(fig)
        paths.append(path.name)
    return paths


def generate_report(config: dict) -> Path:
    output_dir = resolve_path(config["output_dir"])
    metrics_path = output_dir / "metrics.json"
    if not metrics_path.exists():
        raise RuntimeError("metrics.json does not exist; run evaluate first")
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    charts = _charts(metrics, output_dir)
    transcript = metrics.get("transcript", {})
    proxy = metrics.get("retrieval_proxy", {})
    gold = metrics.get("retrieval_gold", {})
    audit = metrics.get("dataset_audit", {})
    per_sample_path = output_dir / "transcript_per_sample.json"
    per_sample = json.loads(per_sample_path.read_text(encoding="utf-8")) if per_sample_path.exists() else []
    evaluation_split = metrics.get("evaluation_split", "test")
    dataset_version = metrics.get("dataset_version", "v1-aligned-101-230")
    expected_samples = metrics.get(
        "expected_samples", metrics.get("expected_test_samples", 182)
    )
    examples = []
    for outcome in ("improved", "unchanged", "degraded"):
        for row in [item for item in per_sample if item.get("outcome") == outcome][:3]:
            examples.append(
                f"| {row['audio_id']} | {outcome} | {row['raw_transcript']} | {row['corrected_transcript']} | {row['reference_transcript']} |"
            )
    report = f"""# ASR Correction Benchmark Report

## Scope and external validity warning

**Benchmark `{dataset_version}` represents only two speakers (Toàn and Trí) and
the locked headline test size is N=104. A future dataset v2 with an independently
verified mapping for IDs 1–100 is required before claiming broader speaker
generalization.**

The smaller test set reduces statistical power and may widen confidence
intervals. A non-significant result must be interpreted together with its effect
size and confidence interval; it does not by itself demonstrate absence of an
effect.

## Methodology

- Paired comparison on the `{evaluation_split}` split; expected N={expected_samples}.
- Dataset v1 retains only independently aligned audio/reference IDs `101–230`.
- A deterministic 20-item cross-check (seed 44) found 20/20 content-aligned
  samples, all WER below 0.5, with mean raw-STT WER 0.08256.
- Baseline uses the cached raw STT transcript; proposed differs only by ASR correction.
- Existing generic `rewrite_query()` is excluded from both voice branches.
- Retrieval proxy is explicitly not treated as true relevance ground truth.

Dataset audit: `{json.dumps(audit, ensure_ascii=False)}`

## Transcript quality

| Metric | Baseline | Proposed |
|---|---:|---:|
| WER | {_pct(transcript.get('baseline_wer'))} | {_pct(transcript.get('proposed_wer'))} |
| CER | {_pct(transcript.get('baseline_cer'))} | {_pct(transcript.get('proposed_cer'))} |

- Relative WER reduction: {_pct(transcript.get('relative_wer_reduction'))}
- Change precision: {_pct(transcript.get('change_precision'))}
- Error-correction recall: {_pct(transcript.get('error_correction_recall'))}
- Over-correction rate: {_pct(transcript.get('over_correction_rate'))}
- Outcomes: `{json.dumps(transcript.get('outcomes', {}), ensure_ascii=False)}`
- Paired WER bootstrap difference and 95% CI (baseline − proposed):
  `{json.dumps(transcript.get('wer_bootstrap_95_ci', {}), ensure_ascii=False)}`
- Paired WER Wilcoxon and rank-biserial effect size:
  `{json.dumps(transcript.get('paired_test', {}), ensure_ascii=False)}`

## Retrieval

- Proxy samples: {proxy.get('samples', 0)}
- Baseline proxy Jaccard@5: {_pct(proxy.get('baseline', {}).get('jaccard_at_5'))}
- Proposed proxy Jaccard@5: {_pct(proxy.get('proposed', {}).get('jaccard_at_5'))}
- Paired proxy Jaccard bootstrap difference and 95% CI:
  `{json.dumps(proxy.get('jaccard_at_5_bootstrap_95_ci', {}), ensure_ascii=False)}`
- Paired proxy Jaccard Wilcoxon and rank-biserial effect size:
  `{json.dumps(proxy.get('jaccard_at_5_paired_test', {}), ensure_ascii=False)}`
- Adjudicated gold samples: {gold.get('samples', 0)}

## System overhead

```json
{json.dumps(metrics.get('system', {}), ensure_ascii=False, indent=2)}
```

## Answer evaluation

- Human graded records: {metrics.get('human_answers', {}).get('graded_records', 0)}
- LLM-judge samples (secondary only): {metrics.get('llm_judge_secondary', {}).get('samples', 0)}
- Estimated token cost: `{json.dumps(metrics.get('estimated_token_cost', {}), ensure_ascii=False)}`

## Representative transcript cases

| Audio ID | Outcome | Raw | Corrected | Reference |
|---:|---|---|---|---|
{chr(10).join(examples) if examples else '| - | Pending inference | - | - | - |'}

## Limitations

{chr(10).join('- ' + item for item in metrics.get('limitations', []))}

## Generated charts

{chr(10).join('- ' + chart for chart in charts) if charts else '- Charts unavailable (matplotlib missing).'}
"""
    path = output_dir / "report.md"
    path.write_text(report, encoding="utf-8")
    return path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="dataset_benchmark/benchmark_config.json")
    args = parser.parse_args()
    generate_report(load_config(args.config))


if __name__ == "__main__":
    main()
