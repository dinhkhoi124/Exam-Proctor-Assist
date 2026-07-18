from __future__ import annotations

import argparse

try:
    from .annotations import create_answer_templates
    from .common import load_config, resolve_path
except ImportError:
    from annotations import create_answer_templates
    from common import load_config, resolve_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="dataset_benchmark/benchmark_config.json")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    config = load_config(args.config)
    output_dir = resolve_path(config["output_dir"])
    create_answer_templates(
        resolve_path(config["manifest"]),
        output_dir / "answer_results.jsonl",
        output_dir / "retrieval_results.jsonl",
        resolve_path(config["annotation_dir"]),
        seed=int(config.get("human_subset_seed", 43)),
        overwrite=args.overwrite,
    )


if __name__ == "__main__":
    main()
