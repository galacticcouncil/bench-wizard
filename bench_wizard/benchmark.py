import json
import os
import subprocess
from typing import List

from bench_wizard.cargo import Cargo
from bench_wizard.config import Config
from bench_wizard.exceptions import BenchmarkCargoException
from bench_wizard.output import Output

from bench_wizard.parser import BenchmarkParser

# TODO: need as configurable option
DIFF_MARGIN = 10  # percent


class Benchmark:
    """ Represents single benchmark"""

    def __init__(self, pallet: str, command: [str], ref_value: float, extrinsics: list):
        self._pallet = pallet
        self._stdout = None
        self._command = command
        self._ref_value = ref_value
        self._extrinsics = extrinsics

        self._extrinsics_results = []

        self._total_time = 0

        self._completed = False
        self._acceptable = False
        self._rerun = False

    @property
    def pallet(self):
        return self._pallet

    @property
    def acceptable(self) -> bool:
        return self._acceptable

    @acceptable.setter
    def acceptable(self, value: bool):
        self._acceptable = value

    @property
    def completed(self) -> bool:
        return self._completed

    @property
    def raw(self) -> bytes:
        return self._stdout

    def run(self, rerun: bool = False) -> None:
        """Run benchmark and parse the result"""
        result = subprocess.run(self._command, capture_output=True)

        if result.returncode != 0:
            raise BenchmarkCargoException(result.stderr.decode("utf-8"))

        self._stdout = result.stdout

        parser = BenchmarkParser(result.stdout)

        self._total_time = parser.total_time(self._extrinsics)

        margin = int(self._ref_value * DIFF_MARGIN / 100)

        diff = int(self._ref_value - self._total_time)

        self.acceptable = diff >= -margin
        self._rerun = rerun
        self._completed = True

    def dump(self, dest: str) -> None:
        """Write benchmark result to a destination file."""
        with open(os.path.join(dest, f"{self._pallet}.results"), "wb") as f:
            f.write(self._stdout)

    @property
    def ref_value(self):
        return self._ref_value

    @property
    def total_time(self):
        return self._total_time

    @property
    def rerun(self):
        return self._rerun

    @property
    def percentage(self) -> float:
        diff = int(self._ref_value - self._total_time)

        percentage = (diff / self._ref_value) * 100

        return percentage


def _prepare_benchmarks(config: Config, reference_values: dict) -> List[Benchmark]:
    benchmarks = []

    for pallet in config.pallets:
        cargo = Cargo(pallet=pallet, template=config.template)
        if config.output_dir:
            output_file = os.path.join(config.output_dir, f"{pallet}.rs")
            cargo.output = output_file

        ref_data = reference_values[pallet]
        ref_value = sum(list(map(lambda x: float(x), ref_data.values())))
        benchmarks.append(
            Benchmark(pallet, cargo.command(), ref_value, ref_data.keys())
        )

    return benchmarks


def _run_benchmarks(benchmarks: List[Benchmark], output: Output, rerun=False) -> None:
    # Note : this can be simplified into one statement

    if rerun:
        [bench.run(rerun) for bench in benchmarks if bench.acceptable is False]
    else:
        output.track(benchmarks)
        for bench in benchmarks:
            # Output updates to easily show progress
            output.update(bench)
            bench.run()
            output.update(bench)


def _build(manifest: str) -> None:
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


def run_pallet_benchmarks(config: Config, to_output: Output) -> None:
    if not config.do_pallet_bench:
        return

    to_output.info("Substrate Node Performance check ... ")

    if config.do_pallet_bench:
        with open(config.reference_values, "r") as f:
            s = json.load(f)

        benchmarks = _prepare_benchmarks(config, s)

        to_output.info("Compiling - this may take a while...")

        _build("node/Cargo.toml")

        to_output.info("Running benchmarks - this may take a while...")

        _run_benchmarks(benchmarks, to_output)

        if [b.acceptable for b in benchmarks].count(False) == 1:
            # if only one failed - rerun it
            _run_benchmarks(benchmarks, to_output, True)

        to_output.results(benchmarks)

        for bench in benchmarks:
            if not config.performance_check:
                # TODO: consolidate the check mess here ( there are too many flags )
                print(bench.raw.decode("utf-8"))

            if config.dump_results:
                bench.dump(config.dump_results)

        to_output.footnote()
