from typing import List


class BenchmarkParser:
    """Parser for substrate benchmark output"""

    """Currently simple straightforward implementation as was done in prototype
       Definitely needs refactoring and be improved.
    """

    def __init__(self, result: bytes):
        self._output = result

        self._pallet = None
        self._extrinsics = dict()

        self.process()

    @property
    def pallet(self) -> str:
        return self._pallet

    def total_time(self, extrinsics: [str]) -> float:
        return sum(
            [
                float(time)
                for (name, time) in self._extrinsics.items()
                if name in extrinsics
            ]
        )

    def process(self) -> None:
        lines = list(map(lambda x: x.decode(), self._output.split(b"\n")))

        for idx, line in enumerate(lines):
            if line.startswith("Pallet:"):
                info = line.split(",")
                self._pallet = info[0].split(":")[1].strip()[1:-1]
                extrinsic = info[1].split(":")[1].strip()[1:-1]
                time = self.extract_time(lines[idx + 1 :])
                self._extrinsics[extrinsic] = time

    @staticmethod
    def extract_time(data: List[str]) -> float:
        for entry in data:
            if entry.startswith("Time"):
                return float(entry.split(" ")[-1])
            if entry.startswith("Pallet:"):
                # we did not find time for some reason
                raise IOError(f"Failed to find time for an extrinsic. Invalid format?!")
