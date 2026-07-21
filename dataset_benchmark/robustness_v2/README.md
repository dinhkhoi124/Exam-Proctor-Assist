# FPT-Assistant ASR Correction Robustness Benchmark v2

Thư mục này chứa benchmark nghiên cứu dùng để trả lời câu hỏi:

> Với pipeline trợ lý giọng nói của FPT-Assistant-v3, thêm một bước LLM sửa
> transcript ASR trước RAG có thực sự tốt hơn việc dùng transcript STT nguyên
> bản hay không?

Đây là namespace nghiên cứu độc lập với benchmark v1. Code benchmark không tự
bật correction trong production và không thay đổi `VOICE_PIPELINE_MODE`.

## 1. Benchmark đang so sánh gì?

### P0 — raw baseline

```text
Audio -> STT -> raw transcript -> RAG -> LLM final answer
```

P0 không sửa transcript và là baseline chính.

### P1 — always correction

```text
Audio -> STT -> raw transcript -> LLM correction
      -> corrected transcript -> RAG -> LLM final answer
```

P1 luôn gọi correction. So sánh nghiên cứu chính là **P1 so với P0** trên cùng
audio variant, STT, RAG corpus, retrieval config và final-answer model.

### P2 — selective correction

```text
Audio -> STT -> risk detector
      |-- risk cao: LLM correction -> RAG -> final answer
      `-- risk thấp: raw transcript -> RAG -> final answer
```

P2 chỉ correction khi detector `heuristic_v1` vượt threshold. Trong run hiện
tại detector chọn `use_raw` cho 650/650 variants, nên P2 bằng P0 và correction
call rate của P2 là 0%.

## 2. Dữ liệu recorded-noise hiện tại

Benchmark sử dụng:

- 130 audio câu hỏi gốc và gold transcript tiếng Việt.
- 2 người nói.
- 40 noise recordings thật do chủ dự án ghi âm.
- 4 loại noise: `fan`, `cafe`, `office`, `speech_babble`.
- Mỗi loại có 3 file dev và 7 file test.
- Dev/test noise pools tách biệt theo recording ID và SHA-256.

Điều kiện audio:

| Condition | Nội dung | Target SNR | Variants/base |
|---|---|---:|---:|
| C0 | Audio sạch nguyên bản | Không áp dụng | 1 |
| C1 | Fan noise thật | 10 hoặc 15 dB | 1 |
| C2 | Cafe và office noise thật | 5 hoặc 10 dB | 2 |
| C3 | Speech-babble noise thật | 0 hoặc 5 dB | 1 |

SNR càng thấp thì noise càng mạnh. Full run có:

- 130 C0 variants.
- 520 recorded-noise variants C1–C3.
- Tổng cộng 650 audio variants.
- 1.950 pipeline rows cho P0/P1/P2.

Bằng chứng chính chỉ lấy `split=test`, `noise_mode=external_asset` và C1–C3:

- 104 test base utterances.
- 416 noisy test variants.
- 28 held-out test noise recordings.
- 1.248 primary pipeline rows.

Clean C0, development split và synthetic run cũ không được gộp vào kết luận
chính.

## 3. Trạng thái và kết quả hiện tại

Recorded-noise inference đã hoàn tất và strict audit xác nhận:

```text
verified: true
expected_variants: 650
expected_pipeline_rows: 1950
failed_or_excluded: 0
api_calls_performed_by_audit: 0
```

Kết quả transcript trên 416 primary test variants:

| Pipeline | Corpus WER | Improved | Unchanged | Degraded |
|---|---:|---:|---:|---:|
| P0 | 16,59% | 0 | 416 | 0 |
| P1 | 16,62% | 11 | 391 | 14 |
| P2 | 16,59% | 0 | 416 | 0 |

P1 so với P0:

- Base-cluster bootstrap 95% CI: `[-0.004611, +0.004865]`.
- Two-way bootstrap 95% CI: `[-0.007079, +0.007075]`.
- Wilcoxon p-value: `0.9553`.
- Holm-adjusted p-value: `1.0`.
- Over-correction: `4/151 = 2,649%` trên các câu P0 vốn đúng hoàn toàn.

Kết luận được phép phát biểu:

> Implementation always-correction hiện tại chưa chứng minh được cải thiện tổng
> thể so với raw-STT baseline trên held-out recorded noise. P1 sửa tốt 11 trường
> hợp nhưng làm xấu 14 trường hợp; các khoảng tin cậy đều chứa 0. Không bật
> correction trong production từ kết quả này.

`speech_babble` có tín hiệu cải thiện cục bộ, nhưng đây chỉ là giả thuyết cho
nghiên cứu tiếp theo, không phải chiến thắng tổng quát.

## 4. Nên đọc file nào trước?

Đọc theo thứ tự sau:

1. `README.md` — tổng quan và điểm bắt đầu.
2. `reports_recorded_noise/TEAM_BENCHMARK_REPORT_VI.md` — báo cáo tiếng Việt để
   trình bày với team.
3. `reports_recorded_noise/robustness_v2_recorded_noise_report.md` — báo cáo
   benchmark được sinh từ evaluator.
4. `reports_recorded_noise/INTERPRETATION_LOCK_SUPPLEMENT.md` — P2,
   over-correction, two-way bootstrap, leave-one-source-out và breakdown theo
   noise.
5. `reports_recorded_noise/local_inference_audit.json` — strict audit, cache
   counts, config provenance và chi phí.
6. `METHODOLOGY.md` và `DATA_CARD.md` — phương pháp và giới hạn dữ liệu.
7. `END_TO_END_BENCHMARK_HANDOFF.md` — hướng dẫn clone, Drive artifact, chạy
   lại, resume và thay model.

Các bảng bằng chứng chi tiết:

```text
reports_recorded_noise/robustness_v2_recorded_noise_summary.json
reports_recorded_noise/robustness_v2_recorded_noise_metrics.csv
reports_recorded_noise/robustness_v2_recorded_noise_sample_level.csv
reports_recorded_noise/robustness_v2_recorded_noise_base_level.csv
```

## 5. Bản đồ thư mục

```text
robustness_v2/
|-- configs/                       # config augmentation/inference/evaluation
|-- scripts/                       # runner, audit, materialization, report
|-- tests/                         # unit/integration tests của benchmark
|-- prompts/                       # prompt LLM judge đã khóa hash
|-- assets/
|   |-- recorded_noise/            # 40 raw M4A, dev/test tách biệt
|   `-- recorded_noise_wav/        # normalized WAV + asset manifest
|-- audio_recorded_noise/          # 520 generated noisy WAVs, lấy từ Drive
|-- manifests/                     # base, plan, generated và run manifests
|-- cache_recorded_noise/          # paid inference cache, lấy từ Drive
|-- checkpoints_recorded_noise/    # input/output hashes và stage metadata
|-- reports_recorded_noise/        # audit, metrics và kết luận
|-- augmentation.py                # audio augmentation primitives
|-- split.py                       # grouped split và leakage controls
|-- pipeline.py                    # P0/P1/P2 và cache keys
|-- evaluation.py                  # WER/CER/statistics/production gates
`-- END_TO_END_BENCHMARK_HANDOFF.md
```

Code benchmark tái sử dụng backend hiện tại:

```text
backend/app/services/stt_service.py
backend/app/services/asr_correction_service.py
backend/app/services/llm_service.py
backend/app/prompts/asr_correction.py
backend/app/prompts/exam_support.py
backend/app/rag/
```

## 6. File nào nằm trên Git và file nào lấy từ Drive?

Git chứa:

- Source code, config, tests và documentation.
- `manifest.csv`, `AUDIO_299.xlsx` và frozen base manifest.
- 40 raw recorded-noise M4A.
- Recorded-noise manifests.
- Checkpoint metadata và reports.

Drive chứa binary/runtime data nặng:

| Archive | Đích sau giải nén | Vai trò |
|---|---|---|
| `Audio_wav-20260708T055213Z-3-001.zip` | `dataset_benchmark/Audio_wav-20260708T055213Z-3-001/` | Clean source WAVs |
| `recorded_noise_wav.zip` | `dataset_benchmark/robustness_v2/assets/` | 40 normalized noise WAVs |
| `audio_recorded_noise.zip` | `dataset_benchmark/robustness_v2/` | 520 noisy benchmark WAVs |
| `cache_recorded_noise.zip` | `dataset_benchmark/robustness_v2/` | Exact paid GPT cache snapshot |
| `rag_snapshot.zip` | `backend/app/rag/` | RAG documents và vector store |

Giải nén sao cho kết quả cuối cùng đúng các path:

```text
dataset_benchmark/Audio_wav-20260708T055213Z-3-001/Audio_wav/101.wav
dataset_benchmark/robustness_v2/assets/recorded_noise_wav/manifest.csv
dataset_benchmark/robustness_v2/audio_recorded_noise/C1/101_c1_v01_recorded_fan.wav
dataset_benchmark/robustness_v2/cache_recorded_noise/stt.jsonl
backend/app/rag/data/
backend/app/rag/vector_store/
```

Không tạo thêm một tầng `FPT-Assistant-v3/FPT-Assistant-v3` khi giải nén.
Drive URL và SHA-256 của bundle phải được chủ dự án gửi qua kênh bàn giao nội
bộ; không commit credential hoặc public link của tài liệu nội bộ vào source.

Minimal fresh-rerun chỉ cần clean WAV + RAG data/vector store; normalized noise
và 520 noisy WAV có thể sinh lại. Exact GPT replay cần thêm toàn bộ WAV đã sinh
và `cache_recorded_noise`.

## 7. Quick start sau khi clone

### 7.1 Chuẩn bị môi trường

Yêu cầu Python 3.11 và `ffmpeg`:

```powershell
py -3.11 -m venv .venv
& '.\.venv\Scripts\Activate.ps1'
& '.\.venv\Scripts\python.exe' -m pip install --upgrade pip
& '.\.venv\Scripts\python.exe' -m pip install -r requirements.txt
& '.\.venv\Scripts\python.exe' -m pip install -r requirements-benchmark.txt

$env:PYTHONUTF8 = '1'
$env:PYTHONIOENCODING = 'utf-8'
```

Các biến môi trường cần cho inference hiện tại:

```text
OPENAI_API_KEY
DATABASE_URL
JWT_SECRET
```

Không commit `.env`.

### 7.2 Chạy test

```powershell
& '.\.venv\Scripts\python.exe' -m pytest `
  dataset_benchmark/robustness_v2/tests `
  backend/tests `
  -q
```

Historical synthetic fixture không nằm trong Git-light handoff; test phụ thuộc
fixture đó sẽ skip nếu artifact cũ không tồn tại.

### 7.3 Materialize và audit recorded noise

Nếu không tải generated WAV snapshot từ Drive, chạy theo thứ tự:

```powershell
& '.\.venv\Scripts\python.exe' -m dataset_benchmark.robustness_v2.scripts.prepare_recorded_noise_assets `
  --raw-root dataset_benchmark/robustness_v2/assets/recorded_noise `
  --output-root dataset_benchmark/robustness_v2/assets/recorded_noise_wav `
  --report dataset_benchmark/robustness_v2/reports_recorded_noise/asset_audit.json

& '.\.venv\Scripts\python.exe' -m dataset_benchmark.robustness_v2.scripts.generate_augmented_dataset `
  --config dataset_benchmark/robustness_v2/configs/augmentation_recorded_noise_config.json `
  --plan-manifest

& '.\.venv\Scripts\python.exe' -m dataset_benchmark.robustness_v2.scripts.generate_augmented_dataset `
  --config dataset_benchmark/robustness_v2/configs/augmentation_recorded_noise_config.json
```

Sau đó verify audio và leakage theo
`END_TO_END_BENCHMARK_HANDOFF.md`.

### 7.4 Dry run trước API trả phí

```powershell
& '.\.venv\Scripts\python.exe' -m dataset_benchmark.robustness_v2.scripts.run_robustness_benchmark `
  --config dataset_benchmark/robustness_v2/configs/local_recorded_noise_inference_config.json `
  --dry-run
```

Không chạy paid inference trước khi review model, cache compatibility, call count
và estimated cost. Các lệnh paid gate, từng stage, resume-after-interruption và
strict audit nằm trong `END_TO_END_BENCHMARK_HANDOFF.md` và
`RECORDED_NOISE_RUNBOOK.md`.

Không dùng `--force-stage` giữa một paid run vì có thể làm mất cache hợp lệ và
gọi API lại.

## 8. Khi muốn benchmark Qwen

Để vẫn trả lời đúng câu hỏi nghiên cứu, chỉ thay **correction model/provider**;
giữ nguyên audio, STT/raw cache, P0, RAG corpus/index, final-answer model, judge,
primary filter và statistics.

Không được chỉ đổi `"correction.model"` trong JSON rồi coi là đã chạy Qwen.
Implementation hiện tại còn phụ thuộc OpenAI client:

- `backend/app/services/asr_correction_service.py` chưa nhận configurable
  `base_url`.
- `backend/app/services/llm_service.py` đang hard-code final-answer GPT model.
- Judge trong runner cũng khởi tạo OpenAI client trực tiếp.

Team cần thêm provider adapter cho OpenAI-compatible Qwen endpoint hoặc local
vLLM/Ollama/Transformers, đồng thời ghi model revision, quantization, decoding,
hardware, prompt hash và usage metadata.

Qwen phải dùng namespace riêng, ví dụ:

```text
cache_recorded_noise_qwen/
checkpoints_recorded_noise_qwen/
reports_recorded_noise_qwen/
manifests/pipeline_recorded_noise_qwen.jsonl
```

Không ghi đè hoặc gắn nhãn lại GPT cache thành Qwen. Chỉ được copy STT cache
sang run Qwen khi audio hashes và toàn bộ STT config khớp.

Xem checklist chi tiết trong `END_TO_END_BENCHMARK_HANDOFF.md`, mục
“Replacing GPT correction with Qwen”.

## 9. Metrics và giới hạn diễn giải

Metric transcript chính là corpus WER. Benchmark còn báo cáo CER,
improved/unchanged/degraded, over-correction, retrieval proxy, LLM judge, cost,
call rate và latency component.

Statistical inference sử dụng paired comparison, base-cluster bootstrap,
two-way bootstrap theo `base_id × noise_source_recording_id`, Wilcoxon,
Holm-adjusted p-value và leave-one-noise-source-out sensitivity.


## 10. Historical artifacts

Pilot C0 10 mẫu và full synthetic C0–C3 run là bằng chứng lịch sử, đã bị
recorded-noise run supersede cho câu hỏi hiện tại. Các artifact sau không cần
cho recorded-noise handoff và được ignore:

```text
audio_augmented/
cache/
checkpoints/
reports/
cache_full/
checkpoints_full/
reports_full/
assets/recorded_noise_quarantine/
```

Không dùng kết quả synthetic cũ để tuyên bố khả năng tổng quát hóa trên noise
thật.

## 11. Quy tắc an toàn và reproducibility

- Mọi run mới phải dùng config và output namespace riêng.
- Không sửa artifact GPT recorded-noise đã khóa.
- Luôn chạy dry-run và strict audit.
- Lưu config hash, input hashes, model revision, prompt hash và seed.
- Không dùng chung dev/test noise recording hoặc crop.
- Không commit `.env`, API key, database secret hoặc JWT secret.
- Không public tài liệu RAG nếu chưa được phép chia sẻ.
- Production không tự thay đổi từ benchmark result.

Canonical execution guide:
`dataset_benchmark/robustness_v2/END_TO_END_BENCHMARK_HANDOFF.md`.
