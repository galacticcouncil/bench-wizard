import json
import os
import subprocess

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

    def run(self, rerun=False):
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
                        process_extrinsic(lines[idx + 1 : idx + 21])
                    )

        self._total_time = sum(list(map(lambda x: float(x), self._extrinsics_results)))
        margin = int(self._ref_value * DIFF_MARGIN / 100)

        diff = int(self._ref_value - self._total_time)

        self._acceptable = diff >= -margin
        self._rerun = rerun

    def dump(self, dest):
        with open(os.path.join(dest, f"{self._pallet}.results"), "wb") as f:
            f.write(self._stdout)


def load_ref_values(filename):
    with open(filename, "r") as f:
        return json.load(f)


def process_extrinsic(data):
    for entry in data:
        if entry.startswith("Time"):
            return float(entry.split(" ")[-1])


def prepare_benchmarks(config: Config, reference_values: dict):

    benchmarks = []

    for pallet in config.pallets:
        command = COMMAND + [f"--pallet={pallet}"]
        ref_data = reference_values[pallet]
        ref_value = sum(list(map(lambda x: float(x), ref_data.values())))
        benchmarks.append(Benchmark(pallet, command, ref_value, ref_data.keys()))

    return benchmarks


def run_benchmarks(benchmarks: [Benchmark], rerun=False):
    # Note : this can be simplified into one statement
    if rerun:
        [bench.run(rerun) for bench in benchmarks if bench._acceptable is False]
    else:
        print("Running benchmarks - this may take a while...")
        [bench.run() for bench in benchmarks]


def show_pallet_result(pallet_result: Benchmark):
    pallet = pallet_result._pallet
    ref_value = pallet_result._ref_value
    current = pallet_result._total_time

    margin = int(ref_value * DIFF_MARGIN / 100)

    diff = int(ref_value - current)

    percentage = f"{(diff / (ref_value + current) ) * 100:.2f}"

    note = "OK" if diff >= -margin else "FAILED"

    diff = f"{diff}"
    times = f"{ref_value:.2f} vs {current:.2f}"

    rerun = "*" if pallet_result._rerun else ""

    print(
        f"{pallet:<25}| {times:^25} | {diff:^14}| {percentage:^14} | {note:^10} | {rerun:^10}"
    )


def run_pallet_benchmarks(config: Config):
    if not config.do_pallet_bench:
        return

    print("Substrate Node Performance check ... ")

    if config.do_pallet_bench:
        s = load_ref_values(config.reference_values)

        benchmarks = prepare_benchmarks(config, s)
        run_benchmarks(benchmarks)

        if [b._acceptable for b in benchmarks].count(False) == 1:
            # of ony failed - rerun it
            run_benchmarks(benchmarks, True)

        print("\nResults:\n\n")

        print(
            f"{'Pallet':^25}|{'Time comparison (µs)':^27}|{'diff* (µs)':^15}|{'diff* (%)':^16}|{'': ^12}| {'Rerun': ^10}"
        )

        for bench in benchmarks:
            show_pallet_result(bench)

            if config.dump_results:
                bench.dump(config.dump_results)

        print("\nNotes:")
        print(
            "* - diff means the difference between reference total time and total benchmark time of current machine"
        )
        print(
            f"* - if diff > {DIFF_MARGIN}% of ref value -> performance is same or better"
        )
        print(
            f"* - If diff < {DIFF_MARGIN}% of ref value -> performance is worse and might not be suitable to run node ( You may ask node devs for further clarifications)"
        )
