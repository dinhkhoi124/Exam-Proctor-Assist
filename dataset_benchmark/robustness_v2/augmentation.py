"""Deterministic waveform augmentation for robustness benchmark v2."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import random
import wave

import numpy as np

from dataset_benchmark.scripts.common import sha256_file, sha256_text


@dataclass(frozen=True)
class AudioData:
    samples: np.ndarray
    sample_rate: int


def read_wav(path: Path) -> AudioData:
    """Read PCM WAV as mono float32 in [-1, 1]."""

    with wave.open(str(path), "rb") as handle:
        channels = handle.getnchannels()
        sample_width = handle.getsampwidth()
        sample_rate = handle.getframerate()
        frames = handle.readframes(handle.getnframes())
    if sample_width != 2:
        raise ValueError(f"Only 16-bit PCM WAV is supported: {path}")
    values = np.frombuffer(frames, dtype="<i2").astype(np.float32) / 32768.0
    if channels > 1:
        values = values.reshape(-1, channels).mean(axis=1)
    return AudioData(values, sample_rate)


def write_wav(path: Path, audio: AudioData) -> None:
    """Atomically write mono 16-bit PCM WAV."""

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    values = np.clip(audio.samples, -1.0, 1.0 - (1 / 32768.0))
    pcm = np.round(values * 32768.0).astype("<i2")
    with wave.open(str(temporary), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(audio.sample_rate)
        handle.writeframes(pcm.tobytes())
    os.replace(temporary, path)


def rms(samples: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(samples, dtype=np.float64)))) if len(samples) else 0.0


def measured_snr_db(clean: np.ndarray, noisy: np.ndarray) -> float:
    noise = noisy.astype(np.float64) - clean.astype(np.float64)
    noise_rms = rms(noise)
    return math.inf if noise_rms == 0 else 20.0 * math.log10(rms(clean) / noise_rms)


def _resample(samples: np.ndarray, target_length: int) -> np.ndarray:
    if target_length <= 0 or not len(samples):
        return np.zeros(max(0, target_length), dtype=np.float32)
    if target_length == len(samples):
        return samples.astype(np.float32, copy=True)
    source_positions = np.linspace(0.0, 1.0, len(samples), endpoint=False)
    target_positions = np.linspace(0.0, 1.0, target_length, endpoint=False)
    return np.interp(target_positions, source_positions, samples).astype(np.float32)


def fit_asset(samples: np.ndarray, target_length: int, rng: random.Random) -> np.ndarray:
    """Deterministically crop or tile an asset to a requested length."""

    if not len(samples):
        raise ValueError("Audio asset is empty")
    if len(samples) >= target_length:
        start = rng.randrange(0, len(samples) - target_length + 1)
        return samples[start : start + target_length].copy()
    repeats = math.ceil(target_length / len(samples))
    tiled = np.tile(samples, repeats)
    offset = rng.randrange(0, len(samples))
    return np.roll(tiled, -offset)[:target_length].copy()


def plan_crop(source_length: int, target_length: int, rng: random.Random) -> dict:
    """Plan an auditable crop/tile operation without reading waveform samples."""

    if source_length <= 0 or target_length < 0:
        raise ValueError("Crop lengths must be positive")
    start = rng.randrange(source_length)
    spans = []
    output_start = 0
    source_start = start
    while output_start < target_length:
        take = min(source_length - source_start, target_length - output_start)
        spans.append(
            {
                "source_start_sample": source_start,
                "source_end_sample": source_start + take,
                "output_start_sample": output_start,
                "output_end_sample": output_start + take,
            }
        )
        output_start += take
        source_start = 0
    return {
        "source_samples": source_length,
        "target_samples": target_length,
        "initial_offset_sample": start,
        "wrap_count": max(0, len(spans) - 1),
        "spans": spans,
    }


def apply_crop_plan(samples: np.ndarray, plan: dict) -> np.ndarray:
    """Materialize a crop plan and validate its recorded source boundaries."""

    if len(samples) != int(plan["source_samples"]):
        raise ValueError("Crop plan source length does not match the waveform")
    pieces = [
        samples[int(span["source_start_sample"]) : int(span["source_end_sample"])]
        for span in plan["spans"]
    ]
    output = np.concatenate(pieces) if pieces else np.zeros(0, dtype=np.float32)
    if len(output) != int(plan["target_samples"]):
        raise RuntimeError("Crop plan produced an unexpected output length")
    return output.astype(np.float32, copy=False)


def audio_sha256(audio: AudioData) -> str:
    """Hash normalized in-memory audio including its sample rate."""

    digest = hashlib.sha256()
    digest.update(int(audio.sample_rate).to_bytes(8, "little", signed=False))
    digest.update(np.asarray(audio.samples, dtype="<f4").tobytes())
    return digest.hexdigest()


def _normalized_noise(samples: np.ndarray, target_rms: float = 0.2) -> np.ndarray:
    samples = np.asarray(samples, dtype=np.float32)
    samples = samples - float(np.mean(samples))
    level = rms(samples)
    if level == 0:
        raise ValueError("Generated noise is silent")
    return (samples * (target_rms / level)).astype(np.float32)


def colored_noise(
    length: int, sample_rate: int, *, seed: int, color: str = "pink"
) -> np.ndarray:
    """Generate deterministic white/pink/brown noise in the frequency domain."""

    if length <= 0:
        raise ValueError("Noise length must be positive")
    exponents = {"white": 0.0, "pink": 1.0, "brown": 2.0}
    if color not in exponents:
        raise ValueError(f"Unsupported noise color: {color}")
    generator = np.random.default_rng(seed)
    white = generator.standard_normal(length)
    spectrum = np.fft.rfft(white)
    frequencies = np.fft.rfftfreq(length, d=1.0 / sample_rate)
    scale = np.ones_like(frequencies)
    nonzero = frequencies > 0
    scale[nonzero] = frequencies[nonzero] ** (-exponents[color] / 2.0)
    scale[~nonzero] = 0.0
    return _normalized_noise(np.fft.irfft(spectrum * scale, n=length))


def generate_procedural_noise(
    generator_name: str,
    length: int,
    sample_rate: int,
    *,
    seed: int,
    parameters: dict,
    donor_tracks: list[tuple[AudioData, dict, float]] | None = None,
) -> AudioData:
    """Generate a split-scoped synthetic noise realization."""

    rng = random.Random(seed)
    donor_tracks = donor_tracks or []
    if generator_name == "synthetic_fan_proxy":
        base = colored_noise(
            length, sample_rate, seed=seed, color=str(parameters.get("color", "pink"))
        )
        time = np.arange(length, dtype=np.float64) / sample_rate
        fundamental = float(parameters["fundamental_hz"])
        harmonics = int(parameters.get("harmonics", 5))
        hum = sum(
            np.sin(2 * np.pi * fundamental * index * time + rng.random() * 2 * np.pi)
            / index
            for index in range(1, harmonics + 1)
        )
        modulation = 1.0 + float(parameters.get("modulation_depth", 0.12)) * np.sin(
            2 * np.pi * float(parameters.get("modulation_hz", 0.4)) * time
        )
        output = base * modulation + 0.08 * hum
    elif generator_name == "synthetic_office_proxy":
        output = colored_noise(
            length, sample_rate, seed=seed, color=str(parameters.get("color", "pink"))
        ).astype(np.float64)
        click_rate = float(parameters.get("click_rate_hz", 1.5))
        click_count = max(1, round(click_rate * length / sample_rate))
        for _ in range(click_count):
            position = rng.randrange(length)
            click_length = min(length - position, max(8, round(sample_rate * 0.012)))
            envelope = np.exp(-np.linspace(0.0, 7.0, click_length))
            output[position : position + click_length] += rng.uniform(0.15, 0.45) * envelope
    elif generator_name in {"in_corpus_speech_babble", "synthetic_cafe_proxy"}:
        if not donor_tracks:
            raise ValueError(f"{generator_name} requires speech donor tracks")
        mixed = np.zeros(length, dtype=np.float64)
        for donor_audio, crop, gain in donor_tracks:
            donor = donor_audio
            if donor.sample_rate != sample_rate:
                donor = AudioData(
                    _resample(
                        donor.samples,
                        round(len(donor.samples) * sample_rate / donor.sample_rate),
                    ),
                    sample_rate,
                )
            mixed += apply_crop_plan(donor.samples, crop).astype(np.float64) * float(gain)
        output = mixed / max(1, len(donor_tracks))
        if generator_name == "synthetic_cafe_proxy":
            ambient = colored_noise(length, sample_rate, seed=seed ^ 0xA5A5A5A5, color="pink")
            output = 0.78 * output + 0.22 * ambient
    else:
        raise ValueError(f"Unknown procedural noise generator: {generator_name}")
    return AudioData(_normalized_noise(np.asarray(output, dtype=np.float32)), sample_rate)


def generate_image_source_rir(
    sample_rate: int, *, parameters: dict
) -> AudioData:
    """Generate a deterministic rectangular-room RIR with the image-source method."""

    room = np.asarray(parameters["room_dimensions_m"], dtype=np.float64)
    source = np.asarray(parameters["source_position_m"], dtype=np.float64)
    microphone = np.asarray(parameters["microphone_position_m"], dtype=np.float64)
    if room.shape != (3,) or source.shape != (3,) or microphone.shape != (3,):
        raise ValueError("Room, source, and microphone positions must have three axes")
    if np.any(room <= 0) or np.any(source <= 0) or np.any(source >= room):
        raise ValueError("Source must be inside a positive room")
    if np.any(microphone <= 0) or np.any(microphone >= room):
        raise ValueError("Microphone must be inside the room")
    rt60 = float(parameters["rt60_sec"])
    volume = float(np.prod(room))
    surface = float(2 * (room[0] * room[1] + room[0] * room[2] + room[1] * room[2]))
    absorption = min(0.95, max(0.05, 0.161 * volume / (surface * rt60)))
    reflection = math.sqrt(1.0 - absorption)
    duration = float(parameters.get("duration_sec", max(0.35, min(1.2, rt60 * 1.25))))
    rir = np.zeros(max(1, round(duration * sample_rate)), dtype=np.float64)
    speed_of_sound = float(parameters.get("speed_of_sound_mps", 343.0))
    max_order = int(parameters.get("max_order", 6))
    for nx in range(-max_order, max_order + 1):
        for ny in range(-max_order, max_order + 1):
            for nz in range(-max_order, max_order + 1):
                indices = np.asarray([nx, ny, nz])
                image = 2.0 * indices * room + np.power(-1.0, indices) * source
                distance = float(np.linalg.norm(image - microphone))
                delay = round(distance / speed_of_sound * sample_rate)
                if delay >= len(rir):
                    continue
                order = abs(nx) + abs(ny) + abs(nz)
                rir[delay] += (reflection**order) / max(distance, 0.1)
    if not np.any(rir):
        raise ValueError("Synthetic RIR contains no arrivals")
    rir /= np.sqrt(np.sum(rir**2))
    return AudioData(rir.astype(np.float32), sample_rate)


def add_background_noise(
    clean: np.ndarray,
    noise: np.ndarray,
    snr_db: float,
    rng: random.Random,
    crop_plan: dict | None = None,
) -> np.ndarray:
    fitted = (
        apply_crop_plan(noise, crop_plan)
        if crop_plan is not None
        else fit_asset(noise, len(clean), rng)
    )
    fitted = fitted - float(np.mean(fitted))
    clean_level, noise_level = rms(clean), rms(fitted)
    if clean_level == 0 or noise_level == 0:
        raise ValueError("Signal and noise must have non-zero RMS")
    target_noise_rms = clean_level / (10.0 ** (snr_db / 20.0))
    return (clean + fitted * (target_noise_rms / noise_level)).astype(np.float32)


def convolve_rir(samples: np.ndarray, rir: np.ndarray) -> np.ndarray:
    if not len(rir) or rms(rir) == 0:
        raise ValueError("RIR must contain non-zero samples")
    normalized_rir = rir.astype(np.float64) / np.sqrt(np.sum(rir.astype(np.float64) ** 2))
    convolved = np.convolve(samples.astype(np.float64), normalized_rir, mode="full")
    return convolved[: len(samples)].astype(np.float32)


def bandpass_phone(samples: np.ndarray, sample_rate: int) -> np.ndarray:
    spectrum = np.fft.rfft(samples)
    frequencies = np.fft.rfftfreq(len(samples), d=1.0 / sample_rate)
    spectrum[(frequencies < 300.0) | (frequencies > 3400.0)] = 0
    return np.fft.irfft(spectrum, n=len(samples)).astype(np.float32)


def codec_quantize(samples: np.ndarray, bits: int = 8) -> np.ndarray:
    """Deterministic mu-law quantization used as a codec-loss proxy."""

    if not 2 <= bits <= 16:
        raise ValueError("codec bits must be between 2 and 16")
    mu = float((2**bits) - 1)
    compressed = np.sign(samples) * np.log1p(mu * np.abs(samples)) / np.log1p(mu)
    quantized = np.round((compressed + 1.0) * mu / 2.0) * 2.0 / mu - 1.0
    expanded = np.sign(quantized) * np.expm1(np.abs(quantized) * np.log1p(mu)) / mu
    return expanded.astype(np.float32)


def apply_operation(
    audio: AudioData,
    operation: dict,
    *,
    rng: random.Random,
    noise_audio: AudioData | None = None,
    rir_audio: AudioData | None = None,
) -> AudioData:
    """Apply one configured waveform operation."""

    name = operation["name"]
    samples, rate = audio.samples, audio.sample_rate
    if name == "background_noise":
        if noise_audio is None:
            raise FileNotFoundError("background_noise requires a noise asset")
        noise = (
            noise_audio.samples
            if noise_audio.sample_rate == rate
            else _resample(
                noise_audio.samples,
                round(len(noise_audio.samples) * rate / noise_audio.sample_rate),
            )
        )
        samples = add_background_noise(
            samples,
            noise,
            float(operation["snr_db"]),
            rng,
            crop_plan=operation.get("asset_crop"),
        )
    elif name == "room_reverberation":
        if rir_audio is None:
            raise FileNotFoundError("room_reverberation requires an RIR asset")
        rir = (
            rir_audio.samples
            if rir_audio.sample_rate == rate
            else _resample(
                rir_audio.samples,
                round(len(rir_audio.samples) * rate / rir_audio.sample_rate),
            )
        )
        samples = convolve_rir(samples, rir)
    elif name == "gain_reduction":
        gain_db = float(operation.get("gain_db", -6.0))
        samples = samples * (10.0 ** (gain_db / 20.0))
    elif name == "mild_clipping":
        threshold = float(operation.get("threshold", 0.8))
        if not 0 < threshold <= 1:
            raise ValueError("clipping threshold must be in (0, 1]")
        samples = np.clip(samples, -threshold, threshold)
    elif name == "bandpass_phone":
        samples = bandpass_phone(samples, rate)
    elif name == "resample_8k":
        down = _resample(samples, round(len(samples) * 8000 / rate))
        samples = _resample(down, len(samples))
    elif name == "codec_compression":
        samples = codec_quantize(samples, int(operation.get("bits", 8)))
    elif name in {"speed_0_9", "speed_1_1", "speed"}:
        factor = float(operation.get("factor", name.removeprefix("speed_").replace("_", ".")))
        if factor <= 0:
            raise ValueError("speed factor must be positive")
        samples = _resample(samples, round(len(samples) / factor))
    else:
        raise ValueError(f"Unknown augmentation operation: {name}")
    return AudioData(np.asarray(samples, dtype=np.float32), rate)


def stable_seed(global_seed: int, *parts: object) -> int:
    digest = hashlib.sha256("|".join(map(str, parts)).encode("utf-8")).digest()
    return (global_seed + int.from_bytes(digest[:8], "big")) % (2**32)


def config_hash(config: dict) -> str:
    return sha256_text(json.dumps(config, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def augment_file(
    source_path: Path,
    output_path: Path,
    operations: list[dict],
    *,
    seed: int,
    noise_path: Path | None = None,
    rir_path: Path | None = None,
    noise_audio: AudioData | None = None,
    rir_audio: AudioData | None = None,
) -> dict:
    """Apply a deterministic chain and return reproducibility metadata."""

    source = read_wav(source_path)
    noise = noise_audio or (read_wav(noise_path) if noise_path else None)
    rir = rir_audio or (read_wav(rir_path) if rir_path else None)
    result = source
    rng = random.Random(seed)
    clipping_requested = any(item["name"] == "mild_clipping" for item in operations)
    for operation in operations:
        result = apply_operation(
            result, operation, rng=rng, noise_audio=noise, rir_audio=rir
        )
    if not clipping_requested:
        peak = float(np.max(np.abs(result.samples))) if len(result.samples) else 0.0
        if peak > 0.999:
            result = AudioData(result.samples * (0.999 / peak), result.sample_rate)
    write_wav(output_path, result)
    return {
        "source_audio_sha256": sha256_file(source_path),
        "noise_sha256": (
            sha256_file(noise_path)
            if noise_path
            else audio_sha256(noise)
            if noise is not None
            else None
        ),
        "rir_sha256": (
            sha256_file(rir_path)
            if rir_path
            else audio_sha256(rir)
            if rir is not None
            else None
        ),
        "output_audio_sha256": sha256_file(output_path),
        "source_duration_sec": len(source.samples) / source.sample_rate,
        "output_duration_sec": len(result.samples) / result.sample_rate,
        "sample_rate": result.sample_rate,
        "peak": float(np.max(np.abs(result.samples))) if len(result.samples) else 0.0,
    }
