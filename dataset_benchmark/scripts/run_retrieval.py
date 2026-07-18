from run_benchmark import load_config, stage_retrieval

if __name__ == "__main__":
    stage_retrieval(load_config("dataset_benchmark/benchmark_config.json"), resume=True)
