import json
import os
import subprocess
from dataclasses import dataclass

from typing import Tuple, Union


@dataclass
class DBPerformanceConfig:
    substrate_dir: str


def db_benchmark(config: DBPerformanceConfig) -> Union[None, Tuple[dict, dict]]:
    print("Performing Database read/write benchmark ( this may take a while ) ... ")

    # clone only if dir does not exit
    if not os.path.isdir(config.substrate_dir):
        print(f"Cloning Substrate repository into {config.substrate_dir}")

        command = f"git clone https://github.com/paritytech/substrate.git {config.substrate_dir}".split(
            " "
        )
        result = subprocess.run(command)

        if result.returncode != 0:
            print("Failed to clone substrate repository")
            return None

    read_benchmark_command = (
        "cargo run --release -p node-bench -- ::trie::read::large --json".split(" ")
    )
    write_benchmark_command = (
        "cargo run --release -p node-bench -- ::trie::write::large --json".split(" ")
    )

    read_result = subprocess.run(
        read_benchmark_command, capture_output=True, cwd=config.substrate_dir
    )

    if read_result.returncode != 0:
        print(f"Failed to run read DB benchmarks: {read_result.stderr}")
        return None

    write_result = subprocess.run(
        write_benchmark_command, capture_output=True, cwd=config.substrate_dir
    )

    if write_result.returncode != 0:
        print(f"Failed to run read DB benchmarks: {write_result.stderr}")
        return None

    read_result = json.loads(read_result.stdout)
    write_result = json.loads(write_result.stdout)
    return read_result, write_result


def display_db_benchmark_results(results: tuple) -> None:
    if not results:
        print("Failed to run db benchmarks")
        return

    print("Database benchmark results:\n")
    print(f"{'Name':^75}|{'Raw average(ns)':^26}|{'Average(ns)':^21}| Reference value")

    for oper in results:
        for result in oper:
            name = result["name"]
            if "RocksDb" in name and "read" in name:
                print(
                    f"{result['name']:<75}| {result['raw_average']:^25}| {result['average']:^20}| 25000"
                )
            elif "RocksDb" in name and "write" in name:
                print(
                    f"{result['name']:<75}| {result['raw_average']:^25}| {result['average']:^20}| 100000"
                )
            elif "read" in name:
                print(
                    f"{result['name']:<75}| {result['raw_average']:^25}| {result['average']:^20}| 8000"
                )
            else:
                print(
                    f"{result['name']:<75}| {result['raw_average']:^25}| {result['average']:^20}| 50000"
                )
    print("")


def run_db_benchmark(config: DBPerformanceConfig):
    results = db_benchmark(config)
    display_db_benchmark_results(results)
