"""Deterministic P0/P1/P2 routing, risk scoring, and cache identities."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
import re
from typing import Any, Mapping, Sequence
import unicodedata

from dataset_benchmark.scripts.common import sha256_text
from dataset_benchmark.scripts.metrics import transcript_errors


PIPELINES = ("P0", "P1", "P2")


def canonical_hash(payload: Any) -> str:
    """Hash a JSON-compatible payload independent of dictionary insertion order."""

    return sha256_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


@dataclass(frozen=True)
class RiskDetectorInput:
    raw_transcript: str
    stt_metadata: Mapping[str, Any] | None = None
    retrieval_metadata: Mapping[str, Any] | None = None
    audio_metadata: Mapping[str, Any] | None = None


@dataclass(frozen=True)
class RiskDetectorResult:
    risk_score: float
    decision: str
    threshold: float
    reasons: tuple[str, ...]
    detector_version: str

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["reasons"] = list(self.reasons)
        return payload


class CorrectionRiskDetector:
    """Interface implemented by deterministic selective-correction detectors."""

    def score(self, sample: RiskDetectorInput) -> RiskDetectorResult:
        raise NotImplementedError


class HeuristicCorrectionRiskDetector(CorrectionRiskDetector):
    """Config-driven, LLM-free detector for the first selective baseline."""

    def __init__(self, config: Mapping[str, Any]):
        self.config = dict(config)
        self.threshold = float(self.config["threshold"])
        self.version = str(self.config.get("version", "heuristic_v1"))
        self.weights = {
            str(key): float(value)
            for key, value in self.config.get("weights", {}).items()
        }

    def _add(self, reasons: list[str], reason: str) -> float:
        weight = self.weights.get(reason, 0.0)
        if weight > 0:
            reasons.append(reason)
        return weight

    def score(self, sample: RiskDetectorInput) -> RiskDetectorResult:
        text = unicodedata.normalize("NFC", sample.raw_transcript or "").strip()
        tokens = re.findall(r"\b\w+\b", text, flags=re.UNICODE)
        reasons: list[str] = []
        score = 0.0

        if not text:
            score += self._add(reasons, "empty_transcript")
        elif len(tokens) < int(self.config.get("minimum_tokens", 3)):
            score += self._add(reasons, "short_transcript")

        allowed_symbols = set(self.config.get("allowed_symbols", "?!.:,;@/_-()[]%+"))
        if any(
            unicodedata.category(char).startswith(("C", "S"))
            and char not in allowed_symbols
            for char in text
        ):
            score += self._add(reasons, "unusual_characters")

        max_repeats = int(self.config.get("max_consecutive_token_repeats", 2))
        folded = [token.casefold() for token in tokens]
        if any(
            len(set(folded[index : index + max_repeats + 1])) == 1
            for index in range(max(0, len(folded) - max_repeats))
        ):
            score += self._add(reasons, "repeated_tokens")

        english_lexicon = {
            value.casefold() for value in self.config.get("english_lexicon", [])
        }
        english_ratio = (
            sum(token in english_lexicon for token in folded) / len(folded)
            if folded
            else 0.0
        )
        if english_ratio > float(self.config.get("english_token_ratio_threshold", 0.5)):
            score += self._add(reasons, "high_english_token_ratio")

        if re.search(r"\b(?:EOS|PEA|VPN|WiFi|FU-Exam|E360)\b", text, re.I):
            score += self._add(reasons, "domain_entity_or_acronym")
        if re.search(
            r"(?:\b\d+(?:\.\d+){1,3}\b|\b\d+(?:\.\d+)*\b|\bK\d{2}\b)",
            text,
            re.I,
        ):
            score += self._add(reasons, "number_ip_or_version")

        retrieval = sample.retrieval_metadata or {}
        candidates = list(retrieval.get("candidates") or [])
        top_score = (
            float(candidates[0].get("combined_score", 0.0)) if candidates else 0.0
        )
        second_score = (
            float(candidates[1].get("combined_score", 0.0))
            if len(candidates) > 1
            else 0.0
        )
        if top_score < float(self.config.get("retrieval_top1_min", 0.2)):
            score += self._add(reasons, "low_retrieval_score")
        if candidates and top_score - second_score < float(
            self.config.get("retrieval_margin_min", 0.1)
        ):
            score += self._add(reasons, "ambiguous_top1_top2_margin")

        stt = sample.stt_metadata or {}
        confidence = stt.get("confidence")
        if confidence is not None and float(confidence) < float(
            self.config.get("stt_confidence_min", 0.7)
        ):
            score += self._add(reasons, "low_stt_confidence")

        bounded_score = round(min(1.0, max(0.0, score)), 6)
        return RiskDetectorResult(
            risk_score=bounded_score,
            decision="correct" if bounded_score >= self.threshold else "use_raw",
            threshold=self.threshold,
            reasons=tuple(reasons),
            detector_version=self.version,
        )


def stt_cache_key(audio_sha256: str, stt_config: Mapping[str, Any]) -> str:
    return canonical_hash(
        {"audio_sha256": audio_sha256, "stt_config": dict(stt_config)}
    )


def correction_cache_key(
    raw_transcript: str, correction_config: Mapping[str, Any]
) -> str:
    required = {
        "model": correction_config["model"],
        "temperature": correction_config["temperature"],
        "service_version": correction_config["service_version"],
        "prompt_sha256": correction_config["prompt_sha256"],
    }
    return canonical_hash(
        {
            "raw_transcript_sha256": sha256_text(raw_transcript or ""),
            **required,
        }
    )


def risk_cache_key(
    raw_transcript: str,
    detector_config: Mapping[str, Any],
    retrieval_config: Mapping[str, Any],
) -> str:
    return canonical_hash(
        {
            "detector_version": detector_config["version"],
            "detector_config_hash": canonical_hash(dict(detector_config)),
            "retrieval_config_hash": canonical_hash(dict(retrieval_config)),
            "raw_transcript_sha256": sha256_text(raw_transcript or ""),
        }
    )


def retrieval_cache_key(
    query: str, retrieval_config: Mapping[str, Any], index_signature: str
) -> str:
    return canonical_hash(
        {
            "query_sha256": sha256_text(query or ""),
            "retrieval_config": dict(retrieval_config),
            "index_signature": index_signature,
        }
    )


def answer_cache_key(
    retrieval_record_hash: str, answer_config: Mapping[str, Any]
) -> str:
    return canonical_hash(
        {
            "retrieval_record_hash": retrieval_record_hash,
            "model": answer_config["model"],
            "temperature": answer_config["temperature"],
            "service_version": answer_config["service_version"],
            "prompt_sha256": answer_config["prompt_sha256"],
        }
    )


def correction_requirements(
    pipelines: Sequence[str], risk_decision: str
) -> tuple[str, ...]:
    """Return pipelines that are permitted to request correction."""

    requested = []
    if "P1" in pipelines:
        requested.append("P1")
    if "P2" in pipelines and risk_decision == "correct":
        requested.append("P2")
    return tuple(requested)


def select_pipeline_transcript(
    pipeline: str,
    *,
    raw_transcript: str,
    correction_record: Mapping[str, Any] | None,
    risk_record: Mapping[str, Any] | None,
) -> tuple[str, str]:
    """Select the exact retrieval input and its source for P0/P1/P2."""

    if pipeline not in PIPELINES:
        raise ValueError(f"Unknown pipeline: {pipeline}")
    if pipeline == "P0":
        return raw_transcript, "raw"
    should_correct = pipeline == "P1" or (
        pipeline == "P2" and (risk_record or {}).get("decision") == "correct"
    )
    if not should_correct:
        return raw_transcript, "raw"
    correction = correction_record or {}
    if correction.get("status") not in {"success", "skipped", "imported"}:
        return raw_transcript, "raw_fallback"
    corrected = str(correction.get("corrected_transcript") or "").strip()
    return (corrected, "corrected") if corrected else (raw_transcript, "raw_fallback")


def tune_thresholds(
    rows: Sequence[Mapping[str, Any]],
    thresholds: Sequence[float],
    *,
    lambda_cost: float,
    lambda_overcorrection: float,
) -> list[dict]:
    """Score threshold candidates using dev-only transcript outcomes."""

    if not rows:
        raise ValueError("Threshold tuning requires non-empty dev rows")
    results = []
    for threshold in thresholds:
        total_gain = 0.0
        calls = 0
        overcorrections = 0
        for row in rows:
            raw = str(row["raw_transcript"])
            corrected = str(row["corrected_transcript"])
            reference = str(row["reference_transcript"])
            selected = float(row["risk_score"]) >= float(threshold)
            raw_wer = float(transcript_errors(reference, raw)["wer"])
            corrected_wer = float(transcript_errors(reference, corrected)["wer"])
            if selected:
                calls += 1
                total_gain += raw_wer - corrected_wer
                if corrected_wer > raw_wer:
                    overcorrections += 1
        count = len(rows)
        quality_gain = total_gain / count
        call_rate = calls / count
        overcorrection_rate = overcorrections / calls if calls else 0.0
        objective = (
            quality_gain
            - lambda_cost * call_rate
            - lambda_overcorrection * overcorrection_rate
        )
        results.append(
            {
                "threshold": float(threshold),
                "quality_gain": quality_gain,
                "correction_call_rate": call_rate,
                "overcorrection_rate": overcorrection_rate,
                "objective": objective if math.isfinite(objective) else 0.0,
            }
        )
    return sorted(results, key=lambda row: (-row["objective"], row["threshold"]))
