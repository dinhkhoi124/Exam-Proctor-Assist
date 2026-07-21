# Báo cáo benchmark LLM ASR Correction trên nhiễu thật

## 1. Câu hỏi nghiên cứu

Benchmark này trả lời câu hỏi:

> Với pipeline trợ lý giọng nói của FPT-Assistant-v3, việc thêm một bước LLM sửa transcript ASR trước RAG có cải thiện chất lượng so với dùng transcript ASR nguyên bản hay không?

So sánh chính là **P1 so với P0** trên cùng audio, cùng STT, cùng hệ thống retrieval, cùng mô hình sinh câu trả lời và cùng cấu hình chạy. Nhờ thiết kế paired này, khác biệt giữa P1 và P0 chủ yếu đến từ bước correction và query được đưa vào RAG.

P2 được đánh giá như một phương án triển khai tiết kiệm hơn: chỉ correction khi bộ phát hiện rủi ro cho rằng transcript có khả năng lỗi.

## 2. Benchmark dựa vào đâu?

Benchmark có bốn lớp bằng chứng:

1. **Gold transcript**: transcript tham chiếu tiếng Việt của từng audio gốc, dùng để tính WER/CER.
2. **Owner-recorded environmental noise**: noise thật do chủ dự án ghi âm, không dùng noise tổng hợp làm bằng chứng chính.
3. **Paired comparison**: mỗi audio variant được chạy qua P0, P1 và P2; kết quả được so sánh trên cùng `variant_id` và gom cụm theo `base_id`.
4. **Audit và provenance**: manifest, SHA-256, cache count, config hash, split leakage và stage metadata được lưu để truy vết lại run.

Bằng chứng chính chỉ gồm **held-out test recorded noise**. Clean C0, development split và benchmark synthetic cũ chỉ là bằng chứng phụ, không được gộp vào con số kết luận chính.

## 3. Dữ liệu benchmark

### 3.1 Audio câu hỏi gốc

- Tổng cộng: **130 base utterances**.
- Có **2 người nói**.
- Mỗi base có audio sạch và transcript tham chiếu.
- Research split được gom theo semantic cluster nhằm tránh trùng/near-duplicate giữa dev và test.
- Đây không phải một fresh independent test hoàn toàn mới, vì kết quả test v1 đã từng được quan sát. Vì vậy kết luận phải giới hạn trong tập nghiên cứu hiện tại.

### 3.2 Noise thật

Có **40 noise recordings duy nhất**, chia tách theo pool:

| Split | Fan | Cafe | Office | Speech babble | Tổng |
|---|---:|---:|---:|---:|---:|
| Dev | 3 | 3 | 3 | 3 | 12 |
| Test | 7 | 7 | 7 | 7 | 28 |

Audit xác nhận 40 raw hashes và 40 decoded-WAV hashes đều duy nhất, không có hash trùng giữa dev và test.

### 3.3 Conditions C0–C3

`C` nghĩa là **audio condition**, tức mức/kiểu điều kiện âm thanh được đưa vào STT.

| Condition | Ý nghĩa | Noise | Target SNR | Variant/base |
|---|---|---|---|---:|
| C0 | Audio sạch nguyên bản | Không | Không áp dụng | 1 |
| C1 | Nhiễu fan, mức nhẹ | Fan ghi âm thật | 10 hoặc 15 dB | 1 |
| C2 | Nhiễu trung bình | Cafe và office ghi âm thật | 5 hoặc 10 dB | 2 |
| C3 | Nhiễu khó | Speech babble ghi âm thật | 0 hoặc 5 dB | 1 |

SNR là **Signal-to-Noise Ratio**. SNR càng thấp thì noise càng mạnh so với tiếng nói; do đó C3 được xem là điều kiện khó nhất.

Từ 130 base utterances, run đầy đủ có:

- 130 C0 variants.
- 130 C1 variants.
- 260 C2 variants, gồm 130 cafe và 130 office.
- 130 C3 variants.
- Tổng: **650 audio variants**.
- Mỗi variant chạy qua 3 pipeline: **1.950 pipeline rows**.

### 3.4 Evidence scope dùng để kết luận

Main result chỉ lấy:

```text
split = test
noise_mode = external_asset
condition in {C1, C2, C3}
```

Sau filter còn:

- **104 test base utterances**.
- **416 noisy test variants**: 104 fan + 104 cafe + 104 office + 104 speech babble.
- **28 independent held-out test noise recordings**.
- **1.248 primary pipeline rows**: 416 variants × 3 pipelines.

Development rows và clean C0 bị loại khỏi bảng kết quả chính để tránh tuning/test leakage và tránh pha trộn clean evidence với noisy evidence.

## 4. Ba pipeline được đánh giá

### P0 — Raw baseline

```text
Audio → STT → raw transcript → RAG retrieval → LLM final answer
```

P0 không sửa transcript. Đây là baseline trực tiếp cho câu hỏi nghiên cứu.

### P1 — Always correct

```text
Audio → STT → raw transcript → LLM correction
      → corrected transcript → RAG retrieval → LLM final answer
```

P1 luôn yêu cầu correction. Đây là treatment chính được so sánh với P0.

### P2 — Selective correction

```text
Audio → STT → raw transcript → risk detector
      ├─ rủi ro cao: LLM correction → corrected query → RAG → final answer
      └─ rủi ro thấp: raw query                    → RAG → final answer
```

Risk detector dùng `heuristic_v1`, threshold `0.6`. Ý tưởng của P2 là chỉ chịu thêm chi phí và rủi ro over-correction khi correction có khả năng hữu ích.

Trong run thực tế, detector trả `use_raw` cho **650/650** variants. Vì vậy correction call rate của P2 là **0%**, và P2 trở thành đúng bằng P0 trong run này. Đây là kết quả của detector hiện tại, không phải bằng chứng rằng selective correction nói chung không thể hoạt động.

## 5. Luồng thực thi benchmark end-to-end

```text
Base manifest + clean WAV + recorded-noise assets
                    ↓
       audit asset/hash/dev-test pool
                    ↓
  lập augmentation plan có seed cố định
                    ↓
 mix C1-C3 theo target SNR + sinh manifest
                    ↓
       verify WAV + audit split leakage
                    ↓
                  STT
                    ↓
             risk detection
                    ↓
              LLM correction
                    ↓
          retrieval cho P0/P1/P2
                    ↓
       sinh final answer cho P0/P1/P2
                    ↓
        LLM judge phụ trợ + evaluate
                    ↓
 bootstrap/Wilcoxon/Holm + report + strict audit
```

Mọi stage dùng cache và checkpoint riêng dưới namespace `robustness_v2`; strict audit không gọi thêm API.

## 6. Metrics và định nghĩa success

### 6.1 Transcript metrics — bằng chứng trực tiếp chính

**WER — Word Error Rate**

```text
WER = (Substitutions + Deletions + Insertions) / số từ trong gold transcript
```

WER càng thấp càng tốt. `Corpus WER` cộng lỗi và số từ trên toàn corpus; đây là metric transcript chính. `Macro WER` lấy trung bình WER từng sample.

**CER — Character Error Rate** giống WER nhưng tính theo ký tự, hữu ích với lỗi dấu và lỗi chính tả tiếng Việt.

**Improved / unchanged / degraded** so sánh P1 hoặc P2 với raw P0 trên đúng cùng audio variant:

- `improved`: WER sau correction thấp hơn raw WER.
- `unchanged`: WER bằng raw WER.
- `degraded`: WER sau correction cao hơn raw WER.

**Over-correction rate** chỉ xét các câu P0 vốn hoàn toàn đúng (`raw_word_errors = 0`):

```text
số câu vốn đúng nhưng correction làm sai / số câu P0 vốn đúng
```

### 6.2 Statistical success

Không kết luận chỉ từ một con số WER thấp hơn. So sánh P1−P0 và P2−P0 dùng:

- **Paired comparison** trên cùng variant.
- **Base-cluster bootstrap**, 5.000 lần, gom theo `base_id`, để không coi nhiều phiên bản noise của cùng câu là các quan sát độc lập.
- **Two-way cluster bootstrap** theo `base_id × noise_source_recording_id`, vì nhiều variant dùng chung câu gốc hoặc noise recording.
- **Wilcoxon signed-rank test** cho paired base-level differences.
- **Holm correction** để điều chỉnh p-value khi kiểm định nhiều pipeline/metric.
- **Leave-one-noise-source-out** để kiểm tra kết luận có bị một noise file cụ thể chi phối không.

Một chiến thắng transcript có sức thuyết phục cần có hướng hiệu ứng tốt hơn P0, confidence interval không bao gồm 0 hoặc bằng chứng thống kê tương ứng, hiệu ứng có ý nghĩa thực tế và không đi kèm over-correction quá mức. Run hiện tại không đạt điều đó.

### 6.3 Retrieval metrics

- **Proxy Jaccard@5**: độ giống nhau giữa tập trang top-5 truy xuất bởi query đang đánh giá và tập trang top-5 khi dùng gold/reference transcript.
- **Proxy overlap recall@5**: tỷ lệ trang trong reference-query top-5 cũng xuất hiện trong candidate top-5.

Đây là **proxy**, không phải true relevance gold. Vì chưa có nhãn người đánh giá tài liệu nào thực sự liên quan, retrieval proxy không đủ để tự tuyên bố thành công production.

### 6.4 Final-answer metrics

LLM judge chấm correctness, groundedness, helpfulness và safety theo thang điểm cấu hình. Tuy nhiên judge được khóa vai trò là **auxiliary only**.

Human answer grading chưa có, nên benchmark chưa cung cấp bằng chứng human task success. Vì vậy không được dùng điểm LLM judge như bằng chứng duy nhất rằng trải nghiệm người dùng tốt hơn.

### 6.5 Operational metrics và production gates

Benchmark còn theo dõi call rate, latency component, API cost và cache provenance. Gate production đã khóa gồm:

- Over-correction rate tối đa: 2%.
- Correction call rate tối đa: 50%.
- p95 latency tối đa: 3.000 ms.
- Cost tối đa: 10 USD/1.000 requests.
- Ít nhất 3 speakers.
- Bắt buộc có true-gold retrieval.
- Bắt buộc có human task-success evaluation.
- Không tự động bật production.

Đây là các gate tổng hợp; đạt một metric riêng lẻ không đồng nghĩa được deploy.

## 7. Kiểm soát chất lượng và leakage

Benchmark đã kiểm tra:

- Không cùng `base_id` giữa dev/test.
- Không exact/normalized transcript duplicate giữa split.
- Không near-semantic duplicate theo ngưỡng đã khóa.
- Không dùng cùng noise hash hoặc cùng decoded noise WAV qua dev/test.
- Không crop overlap qua split.
- Không donor/semantic-cluster leakage.
- 650 manifest rows được audit; `leakage_detected = false`.
- Strict local audit xác nhận đủ cache rows, không có failed/excluded row và mọi stage metadata khớp config hash.

Audit này bảo vệ tính nhất quán và chống các leakage đã biết. Nó không biến research split hiện tại thành một fresh external dataset.

## 8. Kết quả chính

### 8.1 Transcript

| Pipeline | Corpus WER | Corpus CER | Improved | Unchanged | Degraded |
|---|---:|---:|---:|---:|---:|
| P0 | 16,59% | 11,67% | 0 | 416 | 0 |
| P1 | 16,62% | 11,94% | 11 | 391 | 14 |
| P2 | 16,59% | 11,67% | 0 | 416 | 0 |

P1−P0 mean WER difference là `+0.000039`, tức P1 hơi xấu hơn ở point estimate:

- Base-cluster bootstrap 95% CI: `[-0.004611, +0.004865]`.
- Two-way bootstrap 95% CI: `[-0.007079, +0.007075]`.
- Wilcoxon p-value: `0.9553`.
- Holm-adjusted p-value: `1.0`.

Các interval đều chứa 0 rất rõ và p-value không cho thấy khác biệt. Do đó **không có bằng chứng thống kê rằng P1 tốt hơn P0**.

Trong 151 variant mà P0 có WER bằng 0, P1 làm sai 4 variant:

- Over-correction rate: `4/151 = 2,649%`.
- 4 row này là subset của 14 degraded rows.
- Con số này vượt gate production 2% đã khóa.

P2 bằng P0 vì detector không trigger correction.

### 8.2 Theo loại noise

| Noise | P0 WER | P1 WER | Improved / unchanged / degraded | Diễn giải |
|---|---:|---:|---:|---|
| Fan | 11,69% | 12,05% | 2 / 98 / 4 | P1 xấu hơn |
| Cafe | 14,92% | 15,04% | 2 / 99 / 3 | P1 xấu hơn nhẹ |
| Office | 14,44% | 15,04% | 1 / 99 / 4 | P1 xấu hơn |
| Speech babble | 25,30% | 24,34% | 6 / 95 / 3 | Có tín hiệu tốt hơn cục bộ |

Speech babble là hướng đáng nghiên cứu tiếp, nhưng global bootstrap và số nguồn noise hiện tại không cho phép tuyên bố P1 thắng tổng thể.

### 8.3 Retrieval và answer

| Pipeline | Proxy Jaccard@5 | Proxy overlap recall@5 | Judge correctness |
|---|---:|---:|---:|
| P0 | 55,18% | 59,19% | 4,204 |
| P1 | 57,18% | 61,08% | 4,192 |
| P2 | 55,18% | 59,19% | 4,188 |

P1 tăng retrieval proxy nhẹ, nhưng confidence interval chứa 0 và Holm-adjusted p-value là `0.541`; chưa có true-gold retrieval. Judge correctness của P1 không cao hơn P0 và judge chỉ là bằng chứng phụ.

### 8.4 Chi phí và audit run

- Full run: 650 variants, 1.950 rows cho mỗi downstream stage có pipeline dimension.
- Failed/excluded: 0 ở các cache được strict audit.
- STT billable audio: 45,762 phút.
- Fresh API spend của toàn experimental run: **1,696573 USD**.
- Strict audit: `verified = true`.

## 9. Kết luận trình bày với team

Kết luận được dữ liệu hỗ trợ là:

> Trên 416 held-out noisy variants được tạo từ 104 câu hỏi và 28 bản ghi noise test do chủ dự án thu, P1 always-correct không cải thiện WER tổng thể so với P0 raw baseline. P1 sửa tốt 11 trường hợp nhưng làm xấu 14 trường hợp; corpus WER tăng nhẹ từ 16,59% lên 16,62%, và cả base-cluster lẫn two-way bootstrap đều cho khoảng tin cậy chứa 0. P2 selective correction không gọi correction ở bất kỳ trường hợp nào nên bằng P0. Vì vậy implementation correction và risk detector hiện tại chưa đủ bằng chứng để bật production.

Không nên diễn giải thành “LLM correction luôn vô ích”. Kết quả chỉ bác bỏ tuyên bố rằng **implementation hiện tại tốt hơn baseline một cách tổng quát trên benchmark này**. Speech babble cho tín hiệu cục bộ tích cực, phù hợp để tạo giả thuyết và phát triển selective detector tốt hơn.

## 10. Giới hạn cần công khai

- Chỉ có 104 test base utterances, 28 test noise sources và 2 speakers.
- Noise là ghi âm thật nhưng được mix có kiểm soát vào câu nói sạch; không phải toàn bộ audio được thu end-to-end trong môi trường thực địa.
- Research split không phải fresh independent test hoàn toàn mới.
- Retrieval chỉ có proxy, chưa có true relevance gold.
- Chưa có human final-answer/task-success grading.
- Error taxonomy và recoverability annotation chưa hoàn tất.
- Chưa tái dựng end-to-end latency đầy đủ.
- Không được suy rộng kết quả sang domain, speaker hoặc thiết bị khác.

## 11. Artifact và đường dẫn dẫn chứng

Tất cả đường dẫn dưới đây tính từ repository root.

### Thiết kế và cấu hình

| Nội dung | Path |
|---|---|
| Config inference recorded noise | `dataset_benchmark/robustness_v2/configs/local_recorded_noise_inference_config.json` |
| Định nghĩa C0–C3, SNR, seed và split | `dataset_benchmark/robustness_v2/configs/augmentation_recorded_noise_config.json` |
| Config metric, statistics và production gates kế thừa | `dataset_benchmark/robustness_v2/configs/benchmark_v2_config.json` |
| Runbook recorded-noise | `dataset_benchmark/robustness_v2/RECORDED_NOISE_RUNBOOK.md` |
| Runbook bàn giao end-to-end | `dataset_benchmark/robustness_v2/END_TO_END_BENCHMARK_HANDOFF.md` |

### Dataset và manifests

| Nội dung | Path |
|---|---|
| Gold/base source manifest | `dataset_benchmark/manifest.csv` |
| Base snapshot đóng băng | `dataset_benchmark/robustness_v2/manifests/base_manifest_snapshot.jsonl` |
| Noise M4A gốc | `dataset_benchmark/robustness_v2/assets/recorded_noise/` |
| Noise WAV đã chuẩn hóa và inventory | `dataset_benchmark/robustness_v2/assets/recorded_noise_wav/manifest.csv` |
| Augmentation plan | `dataset_benchmark/robustness_v2/manifests/recorded_noise_plan.jsonl` |
| Manifest sau materialization | `dataset_benchmark/robustness_v2/manifests/recorded_noise_generated.jsonl` |
| Pipeline run manifest | `dataset_benchmark/robustness_v2/manifests/pipeline_recorded_noise_manifest.jsonl` |
| 520 noisy WAV đã sinh | `dataset_benchmark/robustness_v2/audio_recorded_noise/` |

### Cache bằng chứng từng stage

| Stage | Path |
|---|---|
| STT transcripts | `dataset_benchmark/robustness_v2/cache_recorded_noise/stt.jsonl` |
| Risk decisions | `dataset_benchmark/robustness_v2/cache_recorded_noise/risk_decisions.jsonl` |
| Corrected transcripts | `dataset_benchmark/robustness_v2/cache_recorded_noise/corrections.jsonl` |
| Retrieval results | `dataset_benchmark/robustness_v2/cache_recorded_noise/retrieval.jsonl` |
| Final answers | `dataset_benchmark/robustness_v2/cache_recorded_noise/final_answers.jsonl` |
| LLM judge results | `dataset_benchmark/robustness_v2/cache_recorded_noise/judge.jsonl` |
| Stage provenance/checkpoints | `dataset_benchmark/robustness_v2/checkpoints_recorded_noise/` |

### Audit và báo cáo kết quả

| Nội dung | Path |
|---|---|
| Noise asset/hash audit | `dataset_benchmark/robustness_v2/reports_recorded_noise/asset_audit.json` |
| Materialization verification | `dataset_benchmark/robustness_v2/reports_recorded_noise/materialization_verification.json` |
| Audio quality/SNR audit | `dataset_benchmark/robustness_v2/reports_recorded_noise/audio_quality_audit.json` |
| Split/leakage audit | `dataset_benchmark/robustness_v2/reports_recorded_noise/split_leakage_audit.json` |
| Strict inference/provenance/cost audit | `dataset_benchmark/robustness_v2/reports_recorded_noise/local_inference_audit.json` |
| Machine-readable summary | `dataset_benchmark/robustness_v2/reports_recorded_noise/robustness_v2_recorded_noise_summary.json` |
| Báo cáo benchmark tự sinh | `dataset_benchmark/robustness_v2/reports_recorded_noise/robustness_v2_recorded_noise_report.md` |
| Metric table | `dataset_benchmark/robustness_v2/reports_recorded_noise/robustness_v2_recorded_noise_metrics.csv` |
| Sample-level evidence | `dataset_benchmark/robustness_v2/reports_recorded_noise/robustness_v2_recorded_noise_sample_level.csv` |
| Base-level statistical evidence | `dataset_benchmark/robustness_v2/reports_recorded_noise/robustness_v2_recorded_noise_base_level.csv` |
| P2, over-correction, two-way bootstrap và noise breakdown | `dataset_benchmark/robustness_v2/reports_recorded_noise/INTERPRETATION_LOCK_SUPPLEMENT.md` |
| Danh sách audio để nghe kiểm tra | `dataset_benchmark/robustness_v2/reports_recorded_noise/LISTENING_SAMPLES.md` |

## 12. Tóm tắt một slide

**Question:** LLM correction trước RAG có tốt hơn raw STT không?

**Data:** 104 test questions × 4 real-noise conditions = 416 paired variants; 28 held-out noise recordings; fan/cafe/office/speech babble.

**Comparison:** P0 raw vs P1 always-correct; P2 selective là phương án phụ.

**Primary metric:** transcript corpus WER, paired cluster-aware statistics.

**Result:** P0 16,59%; P1 16,62%; 11 improved, 14 degraded; two-way 95% CI `[-0.71%, +0.71%]`; Holm-adjusted p = 1,0.

**Decision:** chưa chứng minh correction tốt hơn baseline; không bật production. Tín hiệu speech babble là giả thuyết cho vòng nghiên cứu tiếp theo.
