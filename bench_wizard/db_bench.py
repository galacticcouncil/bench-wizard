import json
import os
import subprocess

from bench_wizard.config import Config


def db_benchmark(config: Config):
    if not config.do_db_bench:
        return

    print("Performing Database benchmark ( this may take a while ) ... ")

    # clone only if dir does not exit
    if not os.path.isdir(config.substrate_repo_path):
        print(f"Cloning Substrate repository into {config.substrate_repo_path}")

        command = f"git clone https://github.com/paritytech/substrate.git {config.substrate_repo_path}".split(
            " "
        )
        result = subprocess.run(command)

        if result.returncode != 0:
            print("Failed to clone substrate repository")
            return

    read_benchmark_command = (
        "cargo run --release -p node-bench -- ::trie::read::large --json".split(" ")
    )
    write_benchmark_command = (
        "cargo run --release -p node-bench -- ::trie::write::large --json".split(" ")
    )

    read_result = subprocess.run(
        read_benchmark_command, capture_output=True, cwd=config.substrate_repo_path
    )

    if read_result.returncode != 0:
        print(f"Failed to run read DB benchmarks: {read_result.stderr}")
        return

    write_result = subprocess.run(
        write_benchmark_command, capture_output=True, cwd=config.substrate_repo_path
    )

    if write_result.returncode != 0:
        print(f"Failed to run read DB benchmarks: {write_result.stderr}")
        return

    read_result = json.loads(read_result.stdout)
    write_result = json.loads(write_result.stdout)
    return read_result, write_result


def display_db_benchmark_results(results):
    if not results:
        return

    print("Database benchmark results:\n")
    print(f"{'Name':^75}|{'Raw average(ns)':^26}|{'Average(ns)':^21}|")

    for oper in results:
        for result in oper:
            print(
                f"{result['name']:<75}| {result['raw_average']:^25}| {result['average']:^20}|"
            )

    print("")


def run_db_benchmark(config: Config):
    results = db_benchmark(config)
    display_db_benchmark_results(results)
