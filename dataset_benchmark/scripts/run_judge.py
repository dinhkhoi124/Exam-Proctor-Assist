from run_benchmark import load_config, stage_judge

if __name__ == "__main__":
    stage_judge(load_config("dataset_benchmark/benchmark_config.json"), resume=True)
