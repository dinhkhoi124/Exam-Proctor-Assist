from run_benchmark import load_config, stage_answers

if __name__ == "__main__":
    stage_answers(load_config("dataset_benchmark/benchmark_config.json"), resume=True)
