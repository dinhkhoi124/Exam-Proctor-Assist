from dataset_benchmark.robustness_v2.split import (
    audit_leakage,
    grouped_split,
    semantic_clusters,
)


def _rows():
    return [
        {"audio_id": "1", "reference_transcript": "Làm sao cấu hình WiFi?", "split": "dev"},
        {"audio_id": "2", "reference_transcript": "làm sao cấu hình wifi", "split": "test"},
        {"audio_id": "3", "reference_transcript": "Nội quy kỳ thi", "split": "test"},
    ]


def test_semantic_clusters_and_grouped_split_keep_duplicates_together():
    rows = _rows()
    clusters = semantic_clusters(rows, 0.8)
    assert clusters[1] == clusters[2]
    assignments = grouped_split(rows, clusters, dev_fraction=0.34, seed=42)
    assert assignments[1] == assignments[2]


def test_leakage_audit_detects_normalized_duplicates_cross_split():
    result = audit_leakage(_rows(), near_duplicate_threshold=0.8)
    assert result["normalized_duplicate_cross_split"] == [[1, 2]]
    assert result["leakage_detected"] is True


def test_variants_of_same_base_cannot_cross_split():
    rows = [
        {"base_id": 1, "split": "dev", "reference_transcript": "nội quy", "augmentation_chain": []},
        {"base_id": 1, "split": "test", "reference_transcript": "nội quy", "augmentation_chain": ["background_noise"]},
    ]
    result = audit_leakage(rows, near_duplicate_threshold=0.8)
    assert result["same_base_id_cross_split"] == [{"base_id": 1, "splits": ["dev", "test"]}]


def test_asset_pool_hash_donor_and_crop_leakage_are_detected():
    crop = {
        "spans": [
            {"source_start_sample": 0, "source_end_sample": 100}
        ]
    }
    rows = [
        {
            "base_id": 1,
            "variant_id": "dev_variant",
            "split": "dev",
            "semantic_cluster": "sc_1",
            "reference_transcript": "nội quy",
            "augmentation_chain": ["background_noise"],
            "noise_split_pool": "test",
            "noise_sha256": "same-noise",
            "noise_recipe_hash": "same-recipe",
            "noise_crop": crop,
            "noise_donor_crops": [],
        },
        {
            "base_id": 2,
            "variant_id": "test_variant",
            "split": "test",
            "semantic_cluster": "sc_2",
            "reference_transcript": "wifi student",
            "augmentation_chain": ["background_noise"],
            "noise_split_pool": "test",
            "noise_sha256": "same-noise",
            "noise_recipe_hash": "same-recipe",
            "noise_crop": crop,
            "noise_donor_crops": [
                {
                    "donor_base_id": 2,
                    "donor_split": "dev",
                    "donor_semantic_cluster": "sc_2",
                    "source_audio_sha256": "donor-hash",
                    "crop": crop,
                }
            ],
        },
    ]
    result = audit_leakage(rows, near_duplicate_threshold=0.8)
    assert result["asset_pool_mismatch"]
    assert result["noise_hash_cross_split"]
    assert result["noise_recipe_hash_cross_split"]
    assert result["crop_overlap_cross_split"]
    assert result["donor_split_mismatch"]
    assert result["target_in_noise_donors"]
    assert result["donor_semantic_cluster_overlap"]
