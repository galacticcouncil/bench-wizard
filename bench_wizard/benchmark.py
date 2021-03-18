import json
import os
import subprocess
from typing import List

from bench_wizard.config import Config
from bench_wizard.exceptions import BenchmarkCargoException
from bench_wizard.output import Output

# TODO: need as configurable option
DIFF_MARGIN = 10  # percent

COMMAND = [
    "cargo",
    "run",
    "--release",
    "--features=runtime-benchmarks",
    "--manifest-path=node/Cargo.toml",
    "--",
    "benchmark",
    "--chain=dev",
    "--steps=5",
    "--repeat=20",
    "--extrinsic=*",
    "--execution=wasm",
    "--wasm-execution=compiled",
    "--heap-pages=4096",
]


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
    def acceptable(self) -> bool:
        return self._acceptable

    @acceptable.setter
    def acceptable(self, value: bool):
        self._acceptable = value

    @property
    def completed(self):
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

        lines = list(map(lambda x: x.decode(), self._stdout.split(b"\n")))

        for idx, line in enumerate(lines):
            if line.startswith("Pallet:"):
                info = line.split(",")
                # pallet_name = info[0].split(":")[1].strip()[1:-1]
                extrinsic = info[1].split(":")[1].strip()[1:-1]
                if extrinsic in self._extrinsics:
                    self._extrinsics_results.append(
                        process_extrinsic(lines[idx + 1: idx + 21])
                    )

        self._total_time = sum(list(map(lambda x: float(x), self._extrinsics_results)))
        margin = int(self._ref_value * DIFF_MARGIN / 100)

        diff = int(self._ref_value - self._total_time)

        self.acceptable = diff >= -margin
        self._rerun = rerun
        self._completed = True

    def dump(self, dest: str) -> None:
        """Write benchmark result to a destination file."""
        with open(os.path.join(dest, f"{self._pallet}.results"), "wb") as f:
            f.write(self._stdout)

    def result_as_str(self) -> str:
        """Return benchmark result as a pre-formatted string."""
        # TODO: refactor to be nice and simple
        pallet = self._pallet
        ref_value = self._ref_value
        current = self._total_time

        margin = int(ref_value * DIFF_MARGIN / 100)

        diff = int(ref_value - current)

        percentage = f"{(diff / (ref_value + current)) * 100:.2f}"

        note = "OK" if diff >= -margin else "FAILED"

        diff = f"{diff}"
        times = f"{ref_value:.2f} vs {current:.2f}"

        rerun = "*" if self._rerun else ""

        return f"{pallet:<25}| {times:^25} | {diff:^14}| {percentage:^14} | {note:^10} | {rerun:^10}"


def process_extrinsic(data: List[str]) -> float:
    for entry in data:
        if entry.startswith("Time"):
            return float(entry.split(" ")[-1])


def _prepare_benchmarks(config: Config, reference_values: dict) -> List[Benchmark]:
    benchmarks = []

    for pallet in config.pallets:
        command = COMMAND + [f"--pallet={pallet}"]
        if config.output_dir:
            output_file = os.path.join(config.output_dir, f"{pallet}.rs")
            command += [f"--output={output_file}"]

        if config.template:
            command += [f"--template={config.template}"]

        ref_data = reference_values[pallet]
        ref_value = sum(list(map(lambda x: float(x), ref_data.values())))
        benchmarks.append(Benchmark(pallet, command, ref_value, ref_data.keys()))

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


def run_pallet_benchmarks(config: Config, to_output: Output) -> None:
    if not config.do_pallet_bench:
        return

    to_output.info("Substrate Node Performance check ... ")

    if config.do_pallet_bench:
        with open(config.reference_values, "r") as f:
            s = json.load(f)

        benchmarks = _prepare_benchmarks(config, s)

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
