import json
import os
import subprocess
from typing import Callable, List

from bench_wizard.config import Config

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
    def __init__(self, pallet: str, command: [str], ref_value: float, extrinsics: list):

        # refactor the usage of this protected members so not called directly
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
    def raw(self) -> bytes:
        return self._stdout

    def run(self, rerun: bool = False) -> None:
        result = subprocess.run(self._command, capture_output=True)
        # TODO: check the return code

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

    def dump(self, dest: str) -> None:
        with open(os.path.join(dest, f"{self._pallet}.results"), "wb") as f:
            f.write(self._stdout)

    def result_as_str(self) -> str:
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


def _run_benchmarks(benchmarks: List[Benchmark], rerun=False) -> None:
    # Note : this can be simplified into one statement
    if rerun:
        [bench.run(rerun) for bench in benchmarks if bench.acceptable is False]
    else:
        [bench.run() for bench in benchmarks]


def run_pallet_benchmarks(config: Config, to_output: Callable[[str], None]) -> None:
    if not config.do_pallet_bench:
        return

    to_output("Substrate Node Performance check ... ")

    if config.do_pallet_bench:
        with open(config.reference_values, "r") as f:
            s = json.load(f)

        benchmarks = _prepare_benchmarks(config, s)

        to_output("Running benchmarks - this may take a while...")
        _run_benchmarks(benchmarks)

        if [b.acceptable for b in benchmarks].count(False) == 1:
            # if only one failed - rerun it
            _run_benchmarks(benchmarks, True)

        to_output("\nResults:\n\n")

        to_output(
            f"{'Pallet':^25}|{'Time comparison (µs)':^27}|{'diff* (µs)':^15}|{'diff* (%)':^16}|{'': ^12}| {'Rerun': ^10}"
        )

        for bench in benchmarks:
            to_output(bench.result_as_str())

            if not config.performance_check:
                # TODO: consolidate the check mess here ( there are too many flags )
                print(bench.raw.decode("utf-8"))

            if config.dump_results:
                bench.dump(config.dump_results)

        to_output("\nNotes:")
        to_output(
            "* - diff means the difference between reference total time and total benchmark time of current machine"
        )
        to_output(
            f"* - if diff > {DIFF_MARGIN}% of ref value -> performance is same or better"
        )
        to_output(
            f"* - If diff < {DIFF_MARGIN}% of ref value -> performance is worse and might not be suitable to run node ( You may ask node devs for further clarifications)"
        )
