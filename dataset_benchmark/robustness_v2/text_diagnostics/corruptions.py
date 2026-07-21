"""Deterministic, auditable text corruptions for diagnostic evaluation."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import random
import re
import unicodedata


CORRUPTION_TYPES = (
    "remove_punctuation",
    "remove_diacritics",
    "homophone_substitution",
    "word_deletion",
    "word_insertion",
    "abbreviation_corruption",
    "code_switch_corruption",
    "number_format_corruption",
    "ip_address_corruption",
    "word_boundary_corruption",
)
SEVERITY_RATES = {1: 0.15, 2: 0.30, 3: 0.50}
TOKEN_RE = re.compile(r"\S+")
NUMBER_RE = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)*(?![\w.])")
IP_RE = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")

HOMOPHONES = {
    "sửa": "sữa",
    "mã": "má",
    "mạng": "mạn",
    "lỗi": "nỗi",
    "truy cập": "truy cặp",
    "tài khoản": "tài khoãng",
}
ABBREVIATIONS = {
    "không": "ko",
    "được": "đc",
    "với": "vs",
    "sinh viên": "sv",
    "tài khoản": "tk",
    "mật khẩu": "mk",
}
CODE_SWITCH = {
    "mật khẩu": "password",
    "tài khoản": "account",
    "đăng nhập": "login",
    "thư điện tử": "email",
    "mạng không dây": "wifi",
    "máy chủ": "server",
}
FILLERS = ("ờ", "à", "kiểu", "thì")


@dataclass(frozen=True)
class CorruptionResult:
    text: str
    applied: bool
    exclusion_reason: str | None
    metadata: dict


def _rng(seed: int, kind: str, text: str) -> random.Random:
    digest = hashlib.sha256(f"{seed}|{kind}|{text}".encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest[:8], "big"))


def _pick_count(size: int, rate: float) -> int:
    return min(size, max(1, round(size * rate))) if size else 0


def _replace_candidates(
    text: str,
    replacements: dict[str, str],
    rate: float,
    rng: random.Random,
) -> tuple[str, list[dict]]:
    candidates = [key for key in replacements if re.search(rf"(?<!\w){re.escape(key)}(?!\w)", text, re.IGNORECASE)]
    rng.shuffle(candidates)
    selected = candidates[: _pick_count(len(candidates), rate)]
    edits: list[dict] = []
    output = text
    for source in selected:
        target = replacements[source]
        output, count = re.subn(
            rf"(?<!\w){re.escape(source)}(?!\w)",
            target,
            output,
            count=1,
            flags=re.IGNORECASE,
        )
        if count:
            edits.append({"from": source, "to": target})
    return output, edits


def _strip_diacritics(token: str) -> str:
    normalized = unicodedata.normalize("NFD", token)
    stripped = "".join(char for char in normalized if unicodedata.category(char) != "Mn")
    return unicodedata.normalize("NFC", stripped).replace("đ", "d").replace("Đ", "D")


def apply_corruption(text: str, kind: str, severity: int, seed: int) -> CorruptionResult:
    """Apply one corruption while retaining the original text as semantic gold."""

    if kind not in CORRUPTION_TYPES:
        raise ValueError(f"Unknown corruption type: {kind}")
    if severity not in SEVERITY_RATES:
        raise ValueError("severity must be one of 1, 2, 3")
    if not text.strip():
        return CorruptionResult(text, False, "empty_source_text", {"edits": [], "rate": SEVERITY_RATES[severity]})

    rate = SEVERITY_RATES[severity]
    rng = _rng(seed, kind, text)
    edits: list[dict] = []
    output = text

    if kind == "remove_punctuation":
        positions = [i for i, char in enumerate(text) if unicodedata.category(char).startswith("P")]
        rng.shuffle(positions)
        selected = set(positions[: _pick_count(len(positions), rate)])
        output = "".join(char for i, char in enumerate(text) if i not in selected)
        edits = [{"position": i, "removed": text[i]} for i in sorted(selected)]
    elif kind == "remove_diacritics":
        tokens = list(TOKEN_RE.finditer(text))
        candidates = [i for i, token in enumerate(tokens) if _strip_diacritics(token.group()) != token.group()]
        rng.shuffle(candidates)
        selected = set(candidates[: _pick_count(len(candidates), rate)])
        parts: list[str] = []
        cursor = 0
        for i, match in enumerate(tokens):
            parts.append(text[cursor : match.start()])
            replacement = _strip_diacritics(match.group()) if i in selected else match.group()
            parts.append(replacement)
            if i in selected:
                edits.append({"from": match.group(), "to": replacement, "token_index": i})
            cursor = match.end()
        parts.append(text[cursor:])
        output = "".join(parts)
    elif kind == "homophone_substitution":
        output, edits = _replace_candidates(text, HOMOPHONES, rate, rng)
    elif kind == "abbreviation_corruption":
        output, edits = _replace_candidates(text, ABBREVIATIONS, rate, rng)
    elif kind == "code_switch_corruption":
        output, edits = _replace_candidates(text, CODE_SWITCH, rate, rng)
    elif kind == "word_deletion":
        tokens = text.split()
        indices = list(range(len(tokens)))
        rng.shuffle(indices)
        selected = set(indices[: min(_pick_count(len(tokens), rate), max(0, len(tokens) - 1))])
        output = " ".join(token for i, token in enumerate(tokens) if i not in selected)
        edits = [{"token_index": i, "removed": tokens[i]} for i in sorted(selected)]
    elif kind == "word_insertion":
        tokens = text.split()
        count = _pick_count(len(tokens), rate)
        for _ in range(count):
            index = rng.randrange(len(tokens) + 1)
            token = rng.choice(FILLERS)
            tokens.insert(index, token)
            edits.append({"token_index": index, "inserted": token})
        output = " ".join(tokens)
    elif kind == "number_format_corruption":
        matches = list(NUMBER_RE.finditer(text))
        if matches:
            chosen = rng.choice(matches)
            source = chosen.group()
            target = source.replace(".", " ").replace(",", " ")
            if target == source:
                target = " ".join(source)
            output = text[: chosen.start()] + target + text[chosen.end() :]
            edits = [{"from": source, "to": target, "position": chosen.start()}]
    elif kind == "ip_address_corruption":
        matches = list(IP_RE.finditer(text))
        if matches:
            chosen = rng.choice(matches)
            source = chosen.group()
            separator = " " if severity < 3 else ","
            target = separator.join(source.split("."))
            output = text[: chosen.start()] + target + text[chosen.end() :]
            edits = [{"from": source, "to": target, "position": chosen.start()}]
    elif kind == "word_boundary_corruption":
        tokens = text.split()
        if len(tokens) >= 2:
            index = rng.randrange(len(tokens) - 1)
            source = f"{tokens[index]} {tokens[index + 1]}"
            target = tokens[index] + tokens[index + 1]
            tokens[index : index + 2] = [target]
            output = " ".join(tokens)
            edits = [{"from": source, "to": target, "token_index": index}]

    applied = output != text and bool(edits)
    reason = None if applied else "no_applicable_source_pattern"
    return CorruptionResult(
        output,
        applied,
        reason,
        {
            "edits": edits,
            "rate": rate,
            "intended_meaning_source": "reference_text",
            "controlled_injection_only": True,
        },
    )
