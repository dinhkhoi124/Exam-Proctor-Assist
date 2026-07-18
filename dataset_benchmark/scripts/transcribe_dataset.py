from run_benchmark import load_config, stage_transcribe

if __name__ == "__main__":
    stage_transcribe(load_config("dataset_benchmark/benchmark_config.json"), resume=True)
