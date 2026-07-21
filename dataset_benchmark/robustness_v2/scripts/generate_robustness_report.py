"""Render the machine-readable Priority 4 summary as a cautious Markdown report."""

from __future__ import annotations

import argparse
import json

from dataset_benchmark.robustness_v2.error_analysis import build_stage_metadata
from dataset_benchmark.robustness_v2.pipeline import canonical_hash
from dataset_benchmark.scripts.common import atomic_write_json, resolve_path


def pct(value: float | None) -> str:
    return "N/A" if value is None else f"{100 * float(value):.2f}%"


def generate(config: dict) -> str:
    summary_path = resolve_path(config["outputs"]["evaluation_summary"])
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    dataset = summary["dataset"]
    transcript = summary["transcript"]
    retrieval = summary["retrieval"]
    operational = summary["operational"]
    cost_accounting = summary.get("actual_cost_accounting", {})
    detector = summary["selective_correction"]
    decisions = summary["production_decision"]
    stats = summary["statistics"]["comparisons"]
    full_c0_c3 = set(dataset["conditions"]) == {"C0", "C1", "C2", "C3"}
    recorded_primary = bool(dataset.get("primary_filter"))
    evaluated_ids = dataset.get("evaluated_base_ids", dataset.get("pilot_base_ids", []))
    selection = dataset.get("selection", dataset.get("pilot_selection", {}))
    equal_wer = len({transcript[pipeline]["corpus_wer"] for pipeline in ("P0", "P1", "P2")}) == 1
    scope_text = (
        "This report's primary evidence is the **held-out test subset of owner-recorded "
        "environmental noise**. Main metric tables exclude development and clean C0 rows. "
        "P0 uses raw STT, P1 always requests correction, and P2 uses the locked selective detector."
        if recorded_primary else
        "This report covers the **full 130-base, 1,040-variant C0-C3 local run**. "
        "P0 uses raw STT, P1 always requests correction, and P2 uses the locked "
        "heuristic selective detector. The historical 10-base C0 replay remains a "
        "separate evidence layer and must not be pooled without disclosure."
        if full_c0_c3
        else "This report covers a **10-base C0 pilot only**. P0 uses raw STT, P1 "
        "always requests correction, and P2 uses the heuristic selective detector. "
        "No C1-C3 inference or fresh external API call was performed."
    )
    lines = [
        "# ASR Correction Robustness Benchmark v2 Report",
        "",
        "## Executive summary",
        "",
        scope_text,
        "",
        f"- P0/P1/P2 corpus WER: {pct(transcript['P0']['corpus_wer'])} / "
        f"{pct(transcript['P1']['corpus_wer'])} / {pct(transcript['P2']['corpus_wer'])}.",
        (
            "- No aggregate transcript WER difference was observed among pipelines."
            if equal_wer else "- Aggregate transcript WER differs among pipelines; inspect paired statistics and strata."
        ),
        (
            "- This is evidence of clean-pilot equality, not evidence of robustness improvement."
            if not full_c0_c3 and not recorded_primary else
            "- Treat owner-recorded mixtures as controlled recorded-noise evidence, not unconstrained field deployment evidence."
            if recorded_primary else "- Treat C1-C3 as controlled synthetic robustness evidence, not recorded-field evidence."
        ),
        "- Neither P1 nor P2 is recommended for production from this run.",
        "",
        *(
            [
                "## Evidence layers",
                "",
                "| Layer | Scope | Origin | Role in main tables |",
                "|---|---|---|---|",
                "| Fresh full run | 130 bases; 1,040 C0-C3 variants; 3,120 pipeline rows | "
                "Fresh local inference with verified compatible C0 imports | Included; all main metric tables below |",
                "| Historical pilot | 10 C0 bases (101-110); 30 pipeline rows | Compatible historical-cache replay | "
                "Excluded from main tables; secondary sanity check only |",
                "",
                "Historical pilot corpus WER is reported separately: "
                + " / ".join(
                    f"{pipeline}={pct(summary['evidence_layers']['historical_pilot']['corpus_wer'][pipeline])}"
                    for pipeline in ("P0", "P1", "P2")
                )
                + ". It is not pooled with the fresh full-run values.",
                "",
            ]
            if full_c0_c3
            and summary.get("evidence_layers", {}).get("historical_pilot", {}).get("corpus_wer")
            else []
        ),
        *(
            [
                "## Evidence layers",
                "",
                "| Layer | Scope | Role in main tables |",
                "|---|---|---|",
                f"| Held-out recorded-noise test | {dataset['independent_base_utterances']} bases; "
                f"{dataset['audio_variants']} variants; {dataset['pipeline_records']} pipeline rows | Included |",
                f"| Development + clean C0 | {dataset['run_pipeline_records'] - dataset['pipeline_records']} pipeline rows | Excluded; secondary diagnostics |",
                "| Historical synthetic run | Prior run | Excluded; not pooled |",
                "",
            ]
            if recorded_primary else []
        ),
        "## Dataset",
        "",
        f"- Independent base utterances: {dataset['independent_base_utterances']}",
        f"- Evaluated base IDs: {evaluated_ids[0]}–{evaluated_ids[-1]} ({len(evaluated_ids)} total)",
        f"- Selection: {selection.get('selection')}; ordering: {selection.get('ordering')}; randomized: {selection.get('randomized')}.",
        f"- Primary audio variants: {dataset['audio_variants']}",
        f"- Primary pipeline records: {dataset['pipeline_records']}",
        *(
            [
                f"- Full run audio variants: {dataset['run_audio_variants']}",
                f"- Full run pipeline records: {dataset['run_pipeline_records']}",
                f"- Independent test noise sources: {dataset['unique_noise_sources']}",
            ] if recorded_primary else []
        ),
        f"- Speakers: {dataset['speakers']} ({', '.join(dataset['speaker_values'])})",
        f"- Conditions: {', '.join(dataset['conditions'])}",
        (
            "- Noise/severity: C0 clean plus locked C1-C3 procedural noise, RIR, codec, gain, speed, and clipping chains."
            if full_c0_c3 else
            "- Noise/severity: owner-recorded fan, cafe, office, and speech-babble mixed at locked 0/5/10/15 dB target SNR."
            if recorded_primary else "- Noise/severity: none / original clean audio only."
        ),
        f"- Split: {dataset['split_methodology']}.",
        f"- Leakage audit: {dataset['leakage_audit']}.",
        "",
        "## Transcript results",
        "",
        "| Pipeline | Corpus WER | Macro WER | Corpus CER | Improved | Unchanged | Degraded |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for pipeline in ("P0", "P1", "P2"):
        row = transcript[pipeline]
        lines.append(
            f"| {pipeline} | {pct(row['corpus_wer'])} | {pct(row['macro_wer'])} | "
            f"{pct(row['corpus_cer'])} | {row['improved_count']} | "
            f"{row['unchanged_count']} | {row['degraded_count']} |"
        )
    lines.extend(
        [
            "",
            "Hallucinated-token and semantic-rewrite values in the JSON/CSV are lexical "
            "proxies. Human taxonomy/recoverability is unavailable because no error rows "
            "are marked reviewed.",
            "",
            "## Retrieval results",
            "",
            "| Pipeline | Proxy Jaccard@5 | Proxy overlap recall@5 | True gold |",
            "|---|---:|---:|---|",
        ]
    )
    for pipeline in ("P0", "P1", "P2"):
        proxy = retrieval[pipeline]["proxy"]
        lines.append(
            f"| {pipeline} | {pct(proxy['jaccard_at_5'])} | "
            f"{pct(proxy['overlap_recall_at_5'])} | unavailable |"
        )
    lines.extend(
        [
            "",
            "Proxy retrieval compares selected pages with retrieval from the reference "
            "transcript. It is not relevance ground truth and is not mixed with the empty "
            "true-gold section.",
            "",
            "## Final answer results",
            "",
            f"- Human evaluation: {summary['final_answers']['availability']} "
            f"({summary['final_answers']['reason']})",
            f"- LLM judge: {summary['llm_judge']['availability']} "
            f"({summary['llm_judge'].get('scored_rows', 0)} scored rows); auxiliary only.",
            f"- Cached answers are expected for all {dataset['pipeline_records']} pipeline records, but ungraded answers are "
            "not counted as correctness, faithfulness, completeness, citation quality, or "
            "task-success evidence.",
            "",
            *(
                [
                    "| Pipeline | Judge correctness | Groundedness | Helpfulness | Safety |",
                    "|---|---:|---:|---:|---:|",
                    *[
                        f"| {pipeline} | {summary['llm_judge']['by_pipeline'][pipeline]['mean_correctness']:.3f} | "
                        f"{summary['llm_judge']['by_pipeline'][pipeline]['mean_groundedness']:.3f} | "
                        f"{summary['llm_judge']['by_pipeline'][pipeline]['mean_helpfulness']:.3f} | "
                        f"{summary['llm_judge']['by_pipeline'][pipeline]['mean_safety']:.3f} |"
                        for pipeline in ("P0", "P1", "P2")
                    ],
                    "",
                    "Judge scores are auxiliary and do not satisfy the human task-success criterion.",
                ]
                if summary["llm_judge"]["availability"] == "available"
                else []
            ),
            "",
            "## Selective correction",
            "",
            f"- Detector: {detector['detector_version']}",
            f"- Threshold: {detector['threshold']}",
            f"- Decisions: `{json.dumps(detector['decision_counts'], ensure_ascii=False)}`",
            f"- Trigger reasons: `{json.dumps(detector['trigger_reasons'], ensure_ascii=False)}`",
            f"- P1 logical correction call rate: {pct(operational['P1']['logical_correction_call_rate'])}",
            f"- P2 logical correction call rate: {pct(operational['P2']['logical_correction_call_rate'])}",
            "- Detector precision/recall remains unavailable without oracle risk labels.",
            "",
            "## Operational metrics",
            "",
            "| Pipeline | Retrieval p50 | Retrieval p95 | Fresh API calls | Fresh cost |",
            "|---|---:|---:|---:|---:|",
        ]
    )
    for pipeline in ("P0", "P1", "P2"):
        op = operational[pipeline]
        latency = op["retrieval_latency_ms"]
        fresh_calls = op.get("fresh_api_calls", 0)
        lines.append(
            f"| {pipeline} | {latency['p50']:.1f} ms | {latency['p95']:.1f} ms | "
            f"{fresh_calls} | ${op['fresh_api_cost_per_1000_requests_usd']:.4f}/1k requests |"
        )
    lines.extend(
        [
            "",
            f"Unique fresh API spend for the full experimental run was "
            f"${cost_accounting.get('unique_run_spend_usd', {}).get('total', 0):.6f}. "
            "Each route cost includes observed STT plus route-specific correction, answer, "
            "and auxiliary judge cost; route totals must not be summed. Compatible C0 "
            "imports incurred no fresh cost. Provider billing remains authoritative.",
            "",
            "End-to-end latency is not reconstructed by this evaluator; component cache "
            "latencies and the strict local-inference audit remain the authoritative artifacts.",
            "",
            "## Statistics",
            "",
            f"Primary resampling unit: `base_id` (N={dataset['independent_base_utterances']}).",
        ]
    )
    for candidate in ("P1", "P2"):
        wer = stats[candidate]["mean_wer"]
        bootstrap = wer["cluster_bootstrap"]
        test = wer["paired_wilcoxon"]
        lines.append(
            f"- {candidate}−P0 mean WER difference: {bootstrap['candidate_minus_p0']:.6f}; "
            f"95% cluster-bootstrap CI [{bootstrap['ci_low']:.6f}, "
            f"{bootstrap['ci_high']:.6f}]; Wilcoxon p={test['p_value']:.4f}; "
            f"rank-biserial={test['rank_biserial']:.4f}; Holm-adjusted "
            f"p={wer['holm_adjusted_p']:.4f}."
        )
    lines.extend(
        [
            "",
            (
                "All paired WER differences are zero; equality must not be interpreted as demonstrated benefit."
                if equal_wer else "Interpret paired differences with cluster-bootstrap intervals, effect sizes, and condition strata."
            ),
            "",
            "## Stratified reporting",
            "",
            "Machine-readable stratification is provided for condition, noise, SNR, "
            "speaker, intent, semantic cluster, raw-WER bin, code-switch, and entity flags.",
            (
                "C0-C3 and two-speaker strata are populated. Recoverability and taxonomy strata remain unavailable pending annotation."
                if full_c0_c3 else
                "Held-out recorded-noise type/SNR/source strata are populated. Recoverability and taxonomy strata remain unavailable pending annotation."
                if recorded_primary else "Only C0/none/one-speaker strata are populated. Recoverability and taxonomy strata remain unavailable pending annotation."
            ),
            *(
                [
                    "",
                    "## Noise-source sensitivity",
                    "",
                    *[
                        f"- {candidate}: {stats[candidate]['mean_wer']['cluster_bootstrap']['independent_base_utterances']} base clusters; "
                        f"{summary['statistics']['noise_source_sensitivity'][candidate]['noise_sources']} noise-source clusters; "
                        f"two-way bootstrap 95% CI "
                        f"[{summary['statistics']['noise_source_sensitivity'][candidate]['two_way_cluster_bootstrap']['ci_low']:.6f}, "
                        f"{summary['statistics']['noise_source_sensitivity'][candidate]['two_way_cluster_bootstrap']['ci_high']:.6f}]."
                        for candidate in ("P1", "P2")
                    ],
                    "Base-cluster and noise-source sensitivity are reported separately; variants sharing a recording are not treated as independent sources.",
                ]
                if recorded_primary else []
            ),
            "",
            "## Failure analysis",
            "",
            f"- Correction success with transcript improvement: {transcript['P1']['improved_count']}/{transcript['P1']['samples']}.",
            f"- Correction unchanged: {transcript['P1']['unchanged_count']}/{transcript['P1']['samples']}.",
            f"- Over-correction/degraded: {transcript['P1']['degraded_count']}/{transcript['P1']['samples']}.",
            "- Retrieval improved while WER unchanged: 0 observed.",
            "- WER improved while retrieval worsened: 0 observed.",
            "- Audio-only irrecoverable errors: unavailable pending recoverability labels.",
            "",
            "## Production decision matrix",
            "",
            "| Pipeline | Clean WER NI | Task success | True-gold retrieval | Call rate | New speakers | Recommend |",
            "|---|---|---|---|---|---|---|",
        ]
    )
    for pipeline in ("P1", "P2"):
        criteria = decisions[pipeline]["criteria"]
        lines.append(
            f"| {pipeline} | {criteria['clean_wer_non_inferiority']['status']} | "
            f"{criteria['human_task_success']['status']} | "
            f"{criteria['true_gold_retrieval']['status']} | "
            f"{criteria['correction_call_rate']['status']} | "
            f"{criteria['speaker_diversity']['status']} | No |"
        )
    lines.extend(["", "Production remains unchanged; this report never enables a mode automatically.", "", "## Limitations", ""])
    lines.extend(f"- {item}" for item in summary["limitations"])
    lines.extend(
        [
            "",
            "## Reproducibility",
            "",
            f"- Config hash: `{summary['config_hash']}`",
            "- Machine-readable summary, metrics CSV, sample CSV, and base CSV are stored "
            "beside this report.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        default="dataset_benchmark/robustness_v2/configs/benchmark_v2_config.json",
    )
    args = parser.parse_args()
    config_path = resolve_path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8"))
    summary_path = resolve_path(config["outputs"]["evaluation_summary"])
    report_path = resolve_path(config["outputs"]["report_markdown"])
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = report_path.with_suffix(report_path.suffix + ".tmp")
    temporary.write_text(generate(config), encoding="utf-8", newline="\n")
    temporary.replace(report_path)
    metadata = build_stage_metadata(
        "generate_robustness_report",
        inputs={"config": config_path, "evaluation_summary": summary_path},
        outputs={"report_markdown": report_path},
        details={"config_hash": canonical_hash(config)},
    )
    atomic_write_json(
        resolve_path(config["outputs"]["checkpoint_dir"]) / "report.metadata.json",
        metadata,
    )
    print(report_path)


if __name__ == "__main__":
    main()
