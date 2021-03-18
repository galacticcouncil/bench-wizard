from dataclasses import dataclass, field
from typing import Optional

# TODO: remove default Hydra pallets - pallets will become required parameter
PALLETS = ["amm", "exchange", "transaction_multi_payment"]


@dataclass
class Config:
    do_db_bench: bool = False
    substrate_repo_path: str = "./substrate"
    do_pallet_bench: bool = True
    performance_check: bool = False
    reference_values: Optional[str] = None
    dump_results: Optional[str] = None

    # Directory
    # TODO: support for file ( but if multiple pallets in one run - different files ?)
    output_dir: Optional[str] = None
    template: Optional[str] = None
    pallets: [str] = field(default_factory=lambda: PALLETS)
