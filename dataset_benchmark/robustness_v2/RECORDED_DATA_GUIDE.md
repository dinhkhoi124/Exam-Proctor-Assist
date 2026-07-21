# Recorded Data Collection Guide

## Scope

Collect 40–60 representative Vietnamese FPT-support utterances from at least
five speakers, including speakers not present in the current corpus. Recorded
audio is an external-validation tier and must never be presented as equivalent
to synthetic augmentation.

## Required conditions

For each speaker, cover a useful subset of quiet room, laptop microphone,
fan/air-conditioner, cafe or speech noise, far-field, and fast or hesitant
speech. Keep the sentence allocation balanced enough to avoid confounding one
speaker with one condition. Record independent sessions for dev and test; do not
reuse the same source recording or cropped noise across splits.

## Recording protocol

1. Obtain documented consent and usage rights before recording.
2. Use lossless PCM WAV where possible and retain the untouched original.
3. Assign opaque `recording_id`, `speaker_id`, and `session_id` values.
4. Measure or consistently categorize microphone distance and environment.
5. Transcribe in UTF-8 Vietnamese, then have a second person verify the text.
6. Calculate SHA-256 from the frozen audio file before entering the manifest.
7. Split by speaker/session and audit exact, normalized, semantic, and asset
   leakage before inference.

## Manifest

Copy `manifests/recorded_data_manifest_template.csv` and complete every
non-optional field. `human_verified` must be `true` only after transcript review;
`consent_recorded` must be `true` before use. Keep gender and region blank when
not collected—never infer them. `reference_source` should identify the approved
prompt or independently supplied utterance without exposing personal data.

## Quality checks

- Audio opens successfully, duration is plausible, and clipping is documented.
- IDs and audio hashes are unique; paths resolve inside the approved data root.
- UTF-8 round-trip preserves Vietnamese diacritics.
- At least five speakers and the planned condition coverage are present.
- Dev/test share no speaker, session, audio hash, or environment recording asset.
- Exclusions are retained with a reason rather than silently dropped.
