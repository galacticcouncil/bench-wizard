from dataclasses import dataclass, field
from typing import Optional

PALLETS = ["amm", "exchange", "transaction_multi_payment"]


@dataclass
class Config:
    do_db_bench: bool = False
    substrate_repo_path: str = "./substrate"
    do_pallet_bench: bool = True
    reference_values: Optional[str] = None
    dump_results: Optional[str] = None
    pallets: [str] = field(default_factory=lambda: PALLETS)
