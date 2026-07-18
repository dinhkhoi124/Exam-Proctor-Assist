from run_benchmark import load_config, stage_correction

if __name__ == "__main__":
    stage_correction(load_config("dataset_benchmark/benchmark_config.json"), resume=True)
