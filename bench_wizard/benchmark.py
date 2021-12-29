from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from typing import List, Optional

from bench_wizard.cargo import Cargo
from bench_wizard.exceptions import BenchmarkCargoException
from bench_wizard.output import Output


@dataclass
class BenchmarksConfig:
    pallets: [str]
    dump_results: Optional[str] = None
    output_dir: Optional[str] = None
    template: Optional[str] = None


class Benchmark:
    """Represents single benchmark"""

    def __init__(self, pallet: str, command: [str]):
        self._pallet = pallet
        self._stdout = None
        self._command = command
        self._total_time = 0

        self._completed = False
        self._acceptable = False
        self._rerun = False

        self._error = False
        self._error_reason = None

    @property
    def pallet(self):
        return self._pallet

    @property
    def completed(self) -> bool:
        return self._completed

    @property
    def is_error(self) -> bool:
        return self._error

    @property
    def raw(self) -> bytes:
        return self._stdout

    def run(self, rerun: bool = False) -> None:
        """Run benchmark and parse the result"""
        result = subprocess.run(self._command, capture_output=True)

        if result.returncode != 0:
            self._error = True
            self._error_reason = result.stderr.decode("utf-8")
            return

        self._stdout = result.stdout
        self._rerun = rerun
        self._completed = True

    def dump(self, dest: str) -> None:
        """Write benchmark result to a destination file."""
        with open(os.path.join(dest, f"{self._pallet}.results"), "wb") as f:
            f.write(self._stdout)

    @property
    def rerun(self):
        return self._rerun


def _prepare_benchmarks(config: BenchmarksConfig) -> List[Benchmark]:
    benchmarks = []

    for pallet in config.pallets:
        cargo = Cargo(pallet=pallet, template=config.template)

        if config.output_dir:
            output_file = os.path.join(config.output_dir, f"{pallet}.rs")
            cargo.output = output_file

        benchmarks.append(Benchmark(pallet, cargo.command()))

    return benchmarks


def _run_benchmarks(benchmarks: List[Benchmark], output: Output) -> None:
    output.track(benchmarks)
    for bench in benchmarks:
        # Output updates to easily show progress
        output.update(bench)
        bench.run()
        output.update(bench)


def _build_with_runtime_features(manifest: str) -> None:
    command = [
        "cargo",
        "build",
        "--release",
        "--features=runtime-benchmarks",
        f"--manifest-path={manifest}",
    ]

    result = subprocess.run(command, capture_output=True)

    if result.returncode != 0:
        raise BenchmarkCargoException(result.stderr.decode("utf-8"))


def run_pallet_benchmarks(config: BenchmarksConfig, to_output: Output) -> None:
    benchmarks = _prepare_benchmarks(config)
    pallets = []
    for bench in benchmarks:
        pallets.append(bench.pallet)

    to_output.info(f"Benchmarking: {pallets}")

    to_output.info("Compiling - this may take a while...")

    _build_with_runtime_features("node/Cargo.toml")

    to_output.info("Running benchmarks - this may take a while...")

    _run_benchmarks(benchmarks, to_output)

    to_output.results(benchmarks)

    if config.dump_results:
        for bench in benchmarks:
            bench.dump(config.dump_results)
