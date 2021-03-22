from typing import Any, TYPE_CHECKING


if TYPE_CHECKING:
    from .benchmark import Benchmark

# TODO: need as configurable option
DIFF_MARGIN = 10  # percent


class Output:
    """A class used to handle console output"""

    def __init__(self, quiet: bool = False):
        self._quiet = quiet
        self._tracker = 0
        self._completed = 1

    def print(self, *objects: Any):
        if self._quiet:
            return

        for item in objects:
            print(item)

    def info(self, msg: str):
        self.print(msg)

    def track(self, benchmarks: ["Benchmark"]):
        self._tracker = len(benchmarks)

    def update(self, benchmark: "Benchmark"):
        print(
            f"Running {self._completed}/{self._tracker} (pallet: {benchmark.pallet})",
            end="\r",
        )
        self._completed += benchmark.completed

    def results(self, benchmarks: ["Benchmark"]):
        self.info("\nResults:\n\n")

        self.info(
            f"{'Pallet':^25}|{'Time comparison (µs)':^27}|{'diff* (µs)':^15}|{'diff* (%)':^16}|{'': ^12}| {'Rerun': ^10}"
        )

        for bench in benchmarks:
            percentage = f"{bench.percentage:.2f}"

            note = "OK" if bench.acceptable else "FAILED"

            diff = f"{(bench.ref_value - bench.total_time):.2f}"
            times = f"{bench.ref_value:.2f} vs {bench.total_time:.2f}"

            rerun = "*" if bench.rerun else ""

            self.print(
                f"{bench.pallet:<25}| {times:^25} | {diff:^14}| {percentage:^14} | {note:^10} | {rerun:^10}"
            )

    def footnote(self):
        self.print("\nNotes:")
        self.print(
            "* - diff means the difference between reference total time and total benchmark time of current machine"
        )
        self.print(
            f"* - if diff > {DIFF_MARGIN}% of ref value -> performance is same or better"
        )
        self.print(
            f"* - If diff < {DIFF_MARGIN}% of ref value -> performance is worse and might not be suitable to run node ( You may ask node devs for further clarifications)"
        )
