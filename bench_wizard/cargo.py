from dataclasses import dataclass
from typing import Optional, List


@dataclass
class Cargo:
    pallet: str
    manifest: str = "node/Cargo.toml"
    chain: str = "dev"
    steps: int = 5
    repeat: int = 20
    extrinsic: str = "*"
    execution: str = "wasm"
    wasm_execution: str = "compiled"
    heap_pages: int = 4096
    output: Optional[str] = None
    template: Optional[str] = None

    def command(self) -> List[str]:
        cmd = [
            "cargo",
            "run",
            "--release",
            "--features=runtime-benchmarks",
            f"--manifest-path={self.manifest}",
            "--",
            "benchmark",
            f"--pallet={self.pallet}",
            f"--chain={self.chain}",
            f"--steps={self.steps}",
            f"--repeat={self.repeat}",
            f"--extrinsic={self.extrinsic}",
            f"--execution={self.execution}",
            f"--wasm-execution={self.wasm_execution}",
            f"--heap-pages={self.heap_pages}",
        ]

        if self.output:
            cmd.append(f"--output={self.output}")
        if self.template:
            cmd.append(f"--template={self.template}")

        return cmd
