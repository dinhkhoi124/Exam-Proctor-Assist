# Controlled Text Diagnostics

This set injects deterministic text errors into frozen reference transcripts.
It is separate from the audio robustness benchmark and must be reported as:

> Controlled error-injection diagnostic set; not primary evidence of performance
> on real ASR errors.

Each manifest row contains the unchanged reference meaning, corrupted text,
corruption type, severity, seed, edit metadata, source-manifest hash, status, and
an explicit exclusion reason when the source has no applicable pattern.

Generate or preview the manifest:

```powershell
.\.venv\Scripts\python.exe -m `
  dataset_benchmark.robustness_v2.scripts.generate_text_diagnostics `
  --config dataset_benchmark/robustness_v2/configs/text_diagnostics_config.json `
  --dry-run
```

Remove `--dry-run` to write the versioned manifest, summary, and stage metadata.
